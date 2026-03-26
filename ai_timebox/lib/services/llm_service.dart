import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../models/belief.dart';
import '../models/enums.dart';
import '../models/task.dart';

class LlmService {
  static const _storage = FlutterSecureStorage();
  static const _apiUrl = 'https://api.openai.com/v1/chat/completions';
  static const _model = 'gpt-4o-mini';
  static const _apiKeyStorageKey = 'openai_api_key';

  Future<String?> getApiKey() async {
    return await _storage.read(key: _apiKeyStorageKey);
  }

  Future<void> setApiKey(String key) async {
    await _storage.write(key: _apiKeyStorageKey, value: key);
  }

  Future<Map<String, dynamic>?> _callLlm(
    String systemPrompt,
    String userMessage,
  ) async {
    final apiKey = await getApiKey();
    if (apiKey == null || apiKey.isEmpty) return null;

    final body = jsonEncode({
      'model': _model,
      'max_tokens': 2048,
      'response_format': {'type': 'json_object'},
      'messages': [
        {'role': 'system', 'content': systemPrompt},
        {'role': 'user', 'content': userMessage},
      ],
    });

    Future<Map<String, dynamic>?> attempt() async {
      final response = await http.post(
        Uri.parse(_apiUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $apiKey',
        },
        body: body,
      );

      if (response.statusCode != 200) return null;

      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      final text = (decoded['choices'] as List<dynamic>)[0]['message']['content'] as String;

      // Strip markdown code fences if present
      final stripped = text.trim().replaceAll(RegExp(r'^```[a-z]*\n?'), '').replaceAll(RegExp(r'\n?```$'), '').trim();

      final result = jsonDecode(stripped);

      if (result is Map<String, dynamic>) return result;
      if (result is List) return {'items': result};
      return null;
    }

    try {
      return await attempt();
    } on FormatException {
      // Retry once on malformed JSON
      try {
        return await attempt();
      } on FormatException {
        return null;
      }
    } catch (_) {
      // Network or other error — no retry
      return null;
    }
  }

  /// Job 1: Parse raw task titles into structured task data.
  Future<List<Map<String, dynamic>>?> parseTasks(
    List<String> rawTitles,
  ) async {
    const systemPrompt = '''
You are a task parsing assistant. Given a list of task titles, return a JSON object with a "tasks" key containing an array where each element has:
- "title": string (cleaned task title)
- "pillar": one of "work", "health", "errand", "social"
- "estimated_minutes": integer (realistic time estimate)
- "task_type": one of "deep_focus", "quick", "outing", "call"

Respond ONLY with valid JSON.
''';

    final userMessage =
        'Parse these tasks:\n${rawTitles.asMap().entries.map((e) => '${e.key + 1}. ${e.value}').join('\n')}';

    final result = await _callLlm(systemPrompt, userMessage);
    if (result == null) return null;

    // Accept either {'items': [...]} or {'tasks': [...]}
    if (result.containsKey('items') && result['items'] is List) {
      return List<Map<String, dynamic>>.from(result['items'] as List);
    }
    if (result.containsKey('tasks') && result['tasks'] is List) {
      return List<Map<String, dynamic>>.from(result['tasks'] as List);
    }
    return null;
  }

  /// Job 2: Generate a daily schedule with slots and an insight.
  Future<Map<String, dynamic>?> generateSchedule({
    required List<Task> tasks,
    required DayType dayType,
    required String wakeTime,
    required String sleepTime,
    required Map<BeliefParameter, Belief> beliefs,
    required String healthPhase,
    required int healthActivitiesThisWeek,
    List<Task> rolledTasks = const [],
  }) async {
    const systemPrompt = '''
You are a compassionate schedule planner. Given a list of tasks and user context, create a realistic and kind daily schedule.

Return a JSON object with:
- "slots": array of schedule slots, each with:
  - "task_id": string or null
  - "slot_type": one of "task", "buffer", "health_nudge", "open"
  - "start_time": "HH:mm"
  - "end_time": "HH:mm"
  - "title": string
  - "pillar": one of "work", "health", "errand", "social" or null
- "insight": string (a short, warm, encouraging insight about today's plan)

Be realistic about time. Include buffer slots between tasks. Add health nudges if health activity count is low. Be compassionate if tasks were rolled over.

Respond ONLY with valid JSON.
''';

    final beliefSummary = beliefs.entries.map((e) {
      return '${e.key.name}: ${e.value.value.toStringAsFixed(2)} (confidence: ${e.value.confidence.toStringAsFixed(2)})';
    }).join(', ');

    final taskList = tasks.asMap().entries.map((e) {
      final t = e.value;
      return '${e.key + 1}. [${t.id}] "${t.title}" | pillar: ${t.pillar.name} | type: ${t.taskType.name} | ${t.estimatedMinutes}min';
    }).join('\n');

    final rolledList = rolledTasks.isEmpty
        ? 'None'
        : rolledTasks.map((t) => '"${t.title}"').join(', ');

    final userMessage = '''
Day type: ${dayType.name}
Wake time: $wakeTime
Sleep time: $sleepTime
Health phase: $healthPhase
Health activities this week: $healthActivitiesThisWeek
Belief summary: $beliefSummary
Rolled over tasks: $rolledList

Tasks to schedule:
$taskList
''';

    return await _callLlm(systemPrompt, userMessage);
  }

  /// Job 3: Generate end-of-day insights based on completion data.
  Future<Map<String, dynamic>?> generateInsights({
    required int completedCount,
    required int totalCount,
    required List<Task> undoneTasks,
    required int healthActivitiesThisWeek,
    required int streakDays,
  }) async {
    const systemPrompt = '''
You are a compassionate daily review assistant. Given completion data, return a JSON object with:
- "daily_insight": string (warm, honest reflection on the day — celebrate wins, acknowledge difficulty without judgment)
- "health_insight": string (gentle observation about health activity, encouraging if low)
- "undone_prompts": array of strings (kind, non-shaming prompts for each undone task — max 3)

Be brief, warm, and human. No toxic positivity. Respond ONLY with valid JSON.
''';

    final undoneList = undoneTasks.isEmpty
        ? 'None'
        : undoneTasks.map((t) => '"${t.title}"').join(', ');

    final userMessage = '''
Completed tasks: $completedCount of $totalCount
Health activities this week: $healthActivitiesThisWeek
Current streak: $streakDays days
Undone tasks: $undoneList
''';

    return await _callLlm(systemPrompt, userMessage);
  }
}
