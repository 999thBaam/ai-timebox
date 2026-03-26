import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../models/belief.dart';
import '../models/day_plan.dart';
import '../models/enums.dart';
import '../models/schedule_slot.dart';
import '../models/task.dart';
import '../models/week_config.dart';
import '../services/belief_engine.dart';
import '../services/health_tracker.dart';
import '../services/llm_service.dart';
import '../services/offline_scheduler.dart';
import '../services/speech_service.dart';
import '../main.dart' show db;
import '../theme.dart';
import '../widgets/energy_check.dart';
import '../widgets/health_nudge.dart';
import '../widgets/task_check_item.dart';
import '../widgets/task_input.dart';
import '../widgets/timeline_block.dart';
import 'review_screen.dart';
import 'settings_screen.dart';
import 'week_screen.dart';

// ---------------------------------------------------------------------------
// DailyScreen (shell with bottom nav)
// ---------------------------------------------------------------------------

class DailyScreen extends StatefulWidget {
  const DailyScreen({super.key});

  @override
  State<DailyScreen> createState() => _DailyScreenState();
}

class _DailyScreenState extends State<DailyScreen> {
  int _selectedTab = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: IndexedStack(
        index: _selectedTab,
        children: const [
          _DailyBody(),
          WeekScreen(),
        ],
      ),
      bottomNavigationBar: _buildBottomNav(),
    );
  }

  Widget _buildBottomNav() {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.background,
        border: Border(
          top: BorderSide(color: AppColors.glassBorder),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            _NavItem(
              icon: Icons.home_rounded,
              label: 'Daily',
              isSelected: _selectedTab == 0,
              onTap: () => setState(() => _selectedTab = 0),
            ),
            _NavItem(
              icon: Icons.calendar_today_rounded,
              label: 'Week',
              isSelected: _selectedTab == 1,
              onTap: () => setState(() => _selectedTab = 1),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isSelected ? AppColors.workPrimary : AppColors.textMuted;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: color, size: 22),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _DailyBody — the real brain-dump / schedule view
// ---------------------------------------------------------------------------

enum _ScreenMode { input, schedule }

class _DailyBody extends StatefulWidget {
  const _DailyBody();

  @override
  State<_DailyBody> createState() => _DailyBodyState();
}

class _DailyBodyState extends State<_DailyBody> {
  // ── State ────────────────────────────────────────────────────────────────
  _ScreenMode _mode = _ScreenMode.input;
  bool _planning = false;

  // Input mode
  final List<Task> _tasks = [];

  // Schedule mode
  List<ScheduleSlot> _slots = [];
  String? _insight;

  // Energy check overlay
  String? _energyCheckTaskId; // non-null while overlay shown

  // Config loaded from DB
  WeekConfig? _weekConfig;
  Map<BeliefParameter, Belief> _beliefs = {};
  List<Task> _rolledTasks = [];

  // Services
  final _llmService = LlmService();
  final _beliefEngine = BeliefEngine();
  final _speechService = SpeechService();
  bool _speechAvailable = false;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final speechInit = _speechService.init();

    final config = await db.getLatestWeekConfig();
    final beliefs = await db.getAllBeliefs();
    final today = _today();
    final existingPlan = await db.getDayPlan(today);
    final todayTasks = await db.getTasksForDate(today);
    final yesterday = today.subtract(const Duration(days: 1));
    final yesterdayTasks = await db.getTasksForDate(yesterday);

    await speechInit;

    if (!mounted) return;

    setState(() {
      _weekConfig = config;
      _beliefs = {for (final b in beliefs) b.parameter: b};
      _speechAvailable = _speechService.isAvailable;

      // Rolled tasks = yesterday's pending tasks
      _rolledTasks =
          yesterdayTasks.where((t) => t.status == TaskStatus.pending).toList();

      if (existingPlan != null) {
        // Resume saved plan
        _tasks.addAll(todayTasks);
        _slots = _parseSlotsFromPlan(existingPlan);
        _insight = existingPlan.insight;
        _mode = _ScreenMode.schedule;
      } else {
        // Load any tasks already added today (e.g. from a previous session)
        _tasks.addAll(todayTasks);
      }
    });
  }

  List<ScheduleSlot> _parseSlotsFromPlan(DayPlan plan) {
    try {
      final decoded = jsonDecode(plan.scheduleJson) as List<dynamic>;
      return decoded
          .map((e) => ScheduleSlot.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  DateTime _today() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning.';
    if (hour < 18) return 'Good afternoon.';
    return 'Good evening.';
  }

  String _daySubtitle() {
    final config = _weekConfig;
    if (config == null) return '';
    final dayNames = [
      'Monday', 'Tuesday', 'Wednesday', 'Thursday',
      'Friday', 'Saturday', 'Sunday',
    ];
    final isoWeekday = DateTime.now().weekday; // 1=Mon..7=Sun
    final dayName = dayNames[isoWeekday - 1];
    final isTeaching = config.teachingDays.contains(isoWeekday);
    final dayType = isTeaching ? 'Teaching day' : 'Free day';
    return '$dayName — $dayType';
  }

  DayType _currentDayType() {
    final config = _weekConfig;
    if (config == null) return DayType.free;
    final isoWeekday = DateTime.now().weekday;
    return config.teachingDays.contains(isoWeekday)
        ? DayType.teaching
        : DayType.free;
  }

  int _suggestionCount() =>
      _slots.where((s) => s.slotType == SlotType.healthNudge).length;

  // ---------------------------------------------------------------------------
  // Task management (Mode 1)
  // ---------------------------------------------------------------------------

  void _onTaskSubmit(String raw) {
    if (raw.trim().isEmpty) return;
    final now = DateTime.now();
    final task = Task(
      id: const Uuid().v4(),
      title: raw.trim(),
      pillar: Pillar.work, // temporary; LLM will update
      estimatedMinutes: 30, // temporary estimate
      taskType: TaskType.quick, // temporary
      status: TaskStatus.pending,
      createdAt: now,
      scheduledDate: _today(),
    );
    setState(() => _tasks.add(task));
  }

  void _editTask(int index) async {
    final task = _tasks[index];
    final controller = TextEditingController(text: task.title);
    final result = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(
          24, 20, 24, MediaQuery.of(ctx).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Edit task',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: controller,
              autofocus: true,
              style: const TextStyle(color: AppColors.textPrimary, fontSize: 15),
              keyboardAppearance: Brightness.dark,
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0x0DFFFFFF),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
              onSubmitted: (val) => Navigator.pop(ctx, val.trim()),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () {
                      Navigator.pop(ctx, '__DELETE__');
                    },
                    child: const Text(
                      'Delete task',
                      style: TextStyle(color: Color(0xFFFB7185), fontSize: 14),
                    ),
                  ),
                ),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(ctx, controller.text.trim()),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.workPrimary,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text('Save', style: TextStyle(color: Colors.white)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
    controller.dispose();

    if (!mounted || result == null) return;

    if (result == '__DELETE__') {
      setState(() => _tasks.removeAt(index));
    } else if (result.isNotEmpty) {
      setState(() {
        _tasks[index] = Task(
          id: task.id,
          title: result,
          pillar: task.pillar,
          estimatedMinutes: task.estimatedMinutes,
          taskType: task.taskType,
          status: task.status,
          createdAt: task.createdAt,
          scheduledDate: task.scheduledDate,
          scheduledTime: task.scheduledTime,
          timesMoved: task.timesMoved,
        );
      });
    }
  }

  void _onMicTap() async {
    if (!_speechAvailable) return;
    await _speechService.startListening(
      onResult: (text) {
        if (text.isNotEmpty && mounted) {
          _onTaskSubmit(text);
        }
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Plan my day (Mode 1 → Mode 2)
  // ---------------------------------------------------------------------------

  Future<void> _planMyDay() async {
    if (_planning || _tasks.isEmpty) return;

    // Check if API key is set; prompt user if not
    final apiKey = await _llmService.getApiKey();
    final hasKey = apiKey != null && apiKey.isNotEmpty;

    if (!hasKey && mounted) {
      final choice = await showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: AppColors.surface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: AppColors.glassBorder),
          ),
          title: const Text(
            'No API Key',
            style: TextStyle(color: AppColors.textPrimary),
          ),
          content: const Text(
            'To generate smart schedules, enter your OpenAI API key in Settings. Or continue with offline mode.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop('settings'),
              child: const Text(
                'Open Settings',
                style: TextStyle(color: AppColors.workPrimary),
              ),
            ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop('offline'),
              child: const Text(
                'Use Offline Mode',
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ),
          ],
        ),
      );

      if (!mounted) return;

      if (choice == 'settings') {
        await Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const SettingsScreen()),
        );
        return; // Don't proceed; user can re-tap after setting key
      }
      // 'offline' or dismissed: fall through and use offline scheduler
    }

    setState(() => _planning = true);

    try {
      final config = _weekConfig;
      final wakeTime = config?.wakeTime ?? '07:00';
      final sleepTime = config?.sleepTime ?? '23:00';
      final dayType = _currentDayType();

      // Step 1: Parse tasks via LLM
      final rawTitles = _tasks.map((t) => t.title).toList();
      final parsed = await _llmService.parseTasks(rawTitles);

      if (parsed != null && parsed.length == _tasks.length) {
        // Update tasks with parsed data
        for (int i = 0; i < _tasks.length; i++) {
          final p = parsed[i];
          final pillar = _parsePillar(p['pillar'] as String?);
          final taskType = _parseTaskType(p['task_type'] as String?);
          final minutes = (p['estimated_minutes'] as num?)?.toInt() ?? 30;
          _tasks[i] = _tasks[i].copyWith(
            pillar: pillar,
            taskType: taskType,
            estimatedMinutes: minutes,
          );
        }
      }

      // Step 2: Save tasks to DB
      for (final task in _tasks) {
        await db.insertTask(task);
      }

      // Step 3: Build health context
      final today = _today();
      final weekLogs = await db.getHealthLogsForWeek(
        today.subtract(Duration(days: today.weekday - 1)),
      );
      final tracker = HealthTracker(
        appDayCount: await db.getCurrentStreak() + 1,
        acceptedNudgesThisWeek: weekLogs.length,
      );

      // Step 4: Generate schedule via LLM
      Map<String, dynamic>? llmResult;
      try {
        llmResult = await _llmService.generateSchedule(
          tasks: _tasks,
          dayType: dayType,
          wakeTime: wakeTime,
          sleepTime: sleepTime,
          beliefs: _beliefs,
          healthPhase: tracker.currentPhase.name,
          healthActivitiesThisWeek: weekLogs.length,
          rolledTasks: _rolledTasks,
        );
      } catch (_) {
        llmResult = null;
      }

      List<ScheduleSlot> slots;
      String? insight;

      if (llmResult != null) {
        final slotsJson = llmResult['slots'] as List<dynamic>?;
        slots = slotsJson
                ?.map((e) =>
                    ScheduleSlot.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [];
        insight = llmResult['insight'] as String?;
      } else {
        // Fallback to offline scheduler
        slots = OfflineScheduler.generate(
          tasks: _tasks,
          beliefs: _beliefs,
          wakeTime: wakeTime,
          sleepTime: sleepTime,
        );
      }

      // Step 5: Save DayPlan
      final scheduleJson =
          jsonEncode(slots.map((s) => s.toJson()).toList());
      final plan = DayPlan(
        id: const Uuid().v4(),
        date: today,
        dayType: dayType,
        wakeTime: wakeTime,
        sleepTime: sleepTime,
        scheduleJson: scheduleJson,
        insight: insight,
      );
      await db.saveDayPlan(plan);

      if (!mounted) return;
      setState(() {
        _slots = slots;
        _insight = insight;
        _mode = _ScreenMode.schedule;
      });
    } finally {
      if (mounted) setState(() => _planning = false);
    }
  }

  Pillar _parsePillar(String? raw) {
    switch (raw?.toLowerCase()) {
      case 'health':
        return Pillar.health;
      case 'errand':
        return Pillar.errand;
      case 'social':
        return Pillar.social;
      default:
        return Pillar.work;
    }
  }

  TaskType _parseTaskType(String? raw) {
    switch (raw?.toLowerCase()) {
      case 'deep_focus':
        return TaskType.deepFocus;
      case 'outing':
        return TaskType.outing;
      case 'call':
        return TaskType.call;
      default:
        return TaskType.quick;
    }
  }

  // ---------------------------------------------------------------------------
  // Task completion (Mode 2)
  // ---------------------------------------------------------------------------

  Future<void> _onTaskTap(ScheduleSlot slot) async {
    if (slot.slotType != SlotType.task) return;
    final taskId = slot.taskId;
    if (taskId == null) return;

    // Mark done
    await db.updateTaskStatus(taskId, TaskStatus.done);

    // Update local list
    final idx = _tasks.indexWhere((t) => t.id == taskId);
    if (idx >= 0) {
      final task = _tasks[idx];
      setState(() => _tasks[idx] = task.copyWith(status: TaskStatus.done));

      // Process task completion for beliefs
      _processTaskCompletionBeliefs(task);

      // Show EnergyCheck for deep focus tasks
      if (task.taskType == TaskType.deepFocus) {
        setState(() {
          _energyCheckTaskId = taskId;
        });
      }
    }
  }

  void _processTaskCompletionBeliefs(Task task) {
    if (_beliefs.isEmpty) return;

    final scheduledTime = task.scheduledTime;
    final startHour = scheduledTime != null
        ? int.tryParse(scheduledTime.split(':').first) ?? DateTime.now().hour
        : DateTime.now().hour;

    final updated = _beliefEngine.processTaskCompletion(
      _beliefs,
      taskStartHour: startHour,
      durationMinutes: task.estimatedMinutes,
    );

    setState(() => _beliefs = updated);
    _saveBeliefs(updated);
  }

  Future<void> _saveBeliefs(Map<BeliefParameter, Belief> beliefs) async {
    for (final belief in beliefs.values) {
      await db.saveBelief(belief);
    }
  }

  void _onEnergyReport(String level) {
    final currentHour = DateTime.now().hour;
    final updated = _beliefEngine.processEnergyReport(
      _beliefs,
      currentHour: currentHour,
      level: level,
    );
    _beliefs = updated;
    _saveBeliefs(updated);
    setState(() {
      _energyCheckTaskId = null;
    });
  }

  void _onEnergyDismiss() {
    setState(() {
      _energyCheckTaskId = null;
    });
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Stack(
        children: [
          if (_mode == _ScreenMode.input) _buildInputMode(),
          if (_mode == _ScreenMode.schedule) _buildScheduleMode(),
          if (_energyCheckTaskId != null) _buildEnergyCheckOverlay(),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Mode 1: Input
  // ---------------------------------------------------------------------------

  Widget _buildInputMode() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      _greeting(),
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  _buildSettingsGear(),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                _daySubtitle(),
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                "What's on your plate?",
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.sectionTitle,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),

        // Task list
        Expanded(
          child: _tasks.isEmpty
              ? const _EmptyTaskHint()
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
                  itemCount: _tasks.length,
                  itemBuilder: (context, i) {
                    final task = _tasks[i];
                    return Dismissible(
                      key: ValueKey(task.id),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 20),
                        child: const Icon(Icons.delete_outline, color: Color(0xFFFB7185)),
                      ),
                      onDismissed: (_) => setState(() => _tasks.removeAt(i)),
                      child: TaskCheckItem(
                        title: task.title,
                        isDone: task.status == TaskStatus.done,
                        onTap: () => _editTask(i),
                      ),
                    );
                  },
                ),
        ),

        // Input + Plan button
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 16),
          child: Column(
            children: [
              TaskInput(
                onSubmit: _onTaskSubmit,
                onMicTap: _onMicTap,
                showMic: _speechAvailable,
              ),
              const SizedBox(height: 14),
              _buildPlanButton(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPlanButton() {
    return GestureDetector(
      onTap: _planning ? null : _planMyDay,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF6366F1), Color(0xFF818CF8)],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Center(
          child: _planning
              ? const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        color: Colors.white,
                        strokeWidth: 2,
                      ),
                    ),
                    SizedBox(width: 10),
                    Text(
                      'Planning your day...',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                )
              : const Text(
                  'Plan my day',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Mode 2: Schedule
  // ---------------------------------------------------------------------------

  Widget _buildScheduleMode() {
    final taskCount = _tasks.length;
    final suggestionCount = _suggestionCount();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header row
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 0),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Today',
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$taskCount task${taskCount == 1 ? '' : 's'}'
                      '${suggestionCount > 0 ? ' · $suggestionCount suggestion${suggestionCount == 1 ? '' : 's'}' : ''}',
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              // Review day link
              GestureDetector(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ReviewScreen()),
                ),
                child: const Padding(
                  padding: EdgeInsets.only(top: 6, right: 14),
                  child: Text(
                    'Review day',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: AppColors.healthPrimary,
                    ),
                  ),
                ),
              ),
              // Edit link
              GestureDetector(
                onTap: () => setState(() => _mode = _ScreenMode.input),
                child: const Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: Text(
                    'Edit',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: AppColors.workPrimary,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              _buildSettingsGear(),
            ],
          ),
        ),

        // Insight banner
        if (_insight != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 14, 24, 0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0x0A818CF8),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0x1A818CF8)),
              ),
              child: Text(
                _insight!,
                style: const TextStyle(
                  fontSize: 12.5,
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
          ),

        const SizedBox(height: 16),

        // Timeline
        Expanded(
          child: _slots.isEmpty
              ? const Center(
                  child: Text(
                    'No schedule yet.',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 14),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                  itemCount: _slots.length,
                  itemBuilder: (context, i) {
                    final slot = _slots[i];
                    return _buildSlotItem(slot, i);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildSlotItem(ScheduleSlot slot, int index) {
    switch (slot.slotType) {
      case SlotType.task:
        final taskId = slot.taskId;
        final task = taskId != null
            ? _tasks.firstWhere(
                (t) => t.id == taskId,
                orElse: () => Task(
                  id: taskId,
                  title: slot.title,
                  pillar: slot.pillar ?? Pillar.work,
                  estimatedMinutes: 30,
                  taskType: TaskType.quick,
                  createdAt: DateTime.now(),
                  scheduledDate: _today(),
                ),
              )
            : null;
        final isDone = task?.status == TaskStatus.done;

        return Opacity(
          opacity: isDone ? 0.45 : 1.0,
          child: Column(
            children: [
              TimelineBlock(
                startTime: slot.startTime,
                endTime: slot.endTime,
                title: slot.title,
                pillar: slot.pillar,
                slotType: slot.slotType,
                onTap: () => _onTaskTap(slot),
              ),
              _buildConnector(),
            ],
          ),
        );

      case SlotType.buffer:
        return _buildBufferSpacer();

      case SlotType.healthNudge:
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(
            children: [
              _buildConnector(),
              HealthNudge(
                title: slot.title,
                subtitle: '${slot.startTime} – ${slot.endTime}',
                onAccept: () {
                  // Log the nudge acceptance — future task
                },
                onDismiss: () {
                  setState(() {
                    _slots = List.from(_slots)..removeAt(
                        _slots.indexWhere(
                          (s) =>
                              s.startTime == slot.startTime &&
                              s.title == slot.title,
                        ),
                      );
                  });
                },
              ),
              _buildConnector(),
            ],
          ),
        );

      case SlotType.open:
        return Column(
          children: [
            TimelineBlock(
              startTime: slot.startTime,
              endTime: slot.endTime,
              title: slot.title,
              pillar: null, // null triggers open/faded styling
              slotType: slot.slotType,
              onTap: () {},
            ),
            _buildConnector(),
          ],
        );
    }
  }

  Widget _buildSettingsGear() {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const SettingsScreen()),
      ),
      child: const Padding(
        padding: EdgeInsets.only(top: 2),
        child: Icon(
          Icons.settings_outlined,
          color: AppColors.textMuted,
          size: 22,
        ),
      ),
    );
  }

  Widget _buildConnector() {
    return Center(
      child: Container(
        width: 2,
        height: 10,
        color: const Color(0x26FFFFFF), // white @15% opacity
      ),
    );
  }

  Widget _buildBufferSpacer() {
    return const SizedBox(height: 6);
  }

  // ---------------------------------------------------------------------------
  // EnergyCheck overlay
  // ---------------------------------------------------------------------------

  Widget _buildEnergyCheckOverlay() {
    return Positioned(
      left: 16,
      right: 16,
      bottom: 16,
      child: EnergyCheck(
        onReport: _onEnergyReport,
        onDismiss: _onEnergyDismiss,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty state hint
// ---------------------------------------------------------------------------

class _EmptyTaskHint extends StatelessWidget {
  const _EmptyTaskHint();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Text(
          'Type a task below and press Enter,\nor tap the mic to speak.',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 14,
            color: AppColors.textMuted,
            height: 1.6,
          ),
        ),
      ),
    );
  }
}
