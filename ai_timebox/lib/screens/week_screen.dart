import 'package:flutter/material.dart';
import '../models/enums.dart';
import '../models/task.dart';
import '../models/week_config.dart';
import '../storage/local_db.dart';
import '../theme.dart';
import '../widgets/day_pill.dart';
import '../widgets/glass_card.dart';
import 'setup_screen.dart';

class WeekScreen extends StatefulWidget {
  const WeekScreen({super.key});

  @override
  State<WeekScreen> createState() => _WeekScreenState();
}

class _WeekScreenState extends State<WeekScreen> {
  // DB
  final _db = LocalDb();
  bool _dbOpen = false;

  // Data
  WeekConfig? _weekConfig;
  int _selectedDayIndex = 0; // 0=Mon..6=Sun
  Map<int, List<Task>> _tasksByDay = {};
  bool _loading = true;

  // Progress counts (across all 7 days)
  int _doneTasks = 0;
  int _movedTasks = 0;
  int _pendingTasks = 0;

  static const List<String> _dayLabels = [
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
  ];

  static const List<String> _fullDayNames = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
  ];

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _db.init();
    _dbOpen = true;
    await _loadData();
  }

  Future<void> _loadData() async {
    final config = await _db.getLatestWeekConfig();

    // Compute the Monday of the current week
    final now = DateTime.now();
    final weekStart = DateTime(now.year, now.month, now.day)
        .subtract(Duration(days: now.weekday - 1));

    // Load tasks for all 7 days
    final tasksByDay = <int, List<Task>>{};
    int done = 0, moved = 0, pending = 0;

    for (int i = 0; i < 7; i++) {
      final day = weekStart.add(Duration(days: i));
      final tasks = await _db.getTasksForDate(day);
      tasksByDay[i] = tasks;
      for (final t in tasks) {
        switch (t.status) {
          case TaskStatus.done:
            done++;
          case TaskStatus.moved:
            moved++;
          default:
            pending++;
        }
      }
    }

    // Default selected day = today (0=Mon..6=Sun)
    final todayIndex = now.weekday - 1; // weekday: 1=Mon → index 0

    if (!mounted) return;
    setState(() {
      _weekConfig = config;
      _tasksByDay = tasksByDay;
      _selectedDayIndex = todayIndex;
      _doneTasks = done;
      _movedTasks = moved;
      _pendingTasks = pending;
      _loading = false;
    });
  }

  @override
  void dispose() {
    if (_dbOpen) _db.close();
    super.dispose();
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  DateTime _weekStart() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day)
        .subtract(Duration(days: now.weekday - 1));
  }

  int _dayNumber(int index) {
    return _weekStart().add(Duration(days: index)).day;
  }

  DayType _dayType(int index) {
    final config = _weekConfig;
    if (config == null) return DayType.free;
    final isoWeekday = index + 1; // index 0 = Monday = 1
    return config.teachingDays.contains(isoWeekday)
        ? DayType.teaching
        : DayType.free;
  }

  bool _isToday(int index) => index == DateTime.now().weekday - 1;

  String _selectedDayLabel() {
    final dayName = _fullDayNames[_selectedDayIndex];
    final type = _dayType(_selectedDayIndex) == DayType.teaching
        ? 'Teaching day'
        : 'Free day';
    return '$dayName — $type';
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: CircularProgressIndicator(color: AppColors.workPrimary),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: 16),
            _buildDayPillRow(),
            const SizedBox(height: 20),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                children: [
                  _buildSelectedDaySection(),
                  const SizedBox(height: 24),
                  _buildWeekProgress(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Text(
            'This week',
            style: TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          GestureDetector(
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const SetupScreen(isUpdate: true),
              ),
            ),
            child: const Text(
              'Update days',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppColors.workPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDayPillRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(7, (i) {
          return DayPill(
            label: _dayLabels[i],
            dayNumber: _dayNumber(i),
            dayType: _dayType(i),
            isToday: _isToday(i),
            taskCount: _tasksByDay[i]?.length ?? 0,
            onTap: () => setState(() => _selectedDayIndex = i),
          );
        }),
      ),
    );
  }

  Widget _buildSelectedDaySection() {
    final tasks = _tasksByDay[_selectedDayIndex] ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _selectedDayLabel(),
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 12),
        GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: tasks.isEmpty
              ? const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'No tasks for this day.',
                    style: TextStyle(
                      fontSize: 13.5,
                      color: AppColors.textMuted,
                    ),
                  ),
                )
              : Column(
                  children: tasks
                      .map((t) => _buildTaskRow(t))
                      .toList(),
                ),
        ),
      ],
    );
  }

  Widget _buildTaskRow(Task task) {
    final durationLabel = task.estimatedMinutes < 60
        ? '${task.estimatedMinutes}m'
        : '${(task.estimatedMinutes / 60).toStringAsFixed(1)}h';

    final isDone = task.status == TaskStatus.done;
    final isMoved = task.status == TaskStatus.moved;

    Color titleColor = AppColors.textPrimary;
    TextDecoration? decoration;
    if (isDone) {
      titleColor = AppColors.textMuted;
      decoration = TextDecoration.lineThrough;
    } else if (isMoved) {
      titleColor = AppColors.textMuted;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              task.title,
              style: TextStyle(
                fontSize: 13.5,
                color: titleColor,
                decoration: decoration,
                decorationColor: titleColor,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            durationLabel,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textMuted,
            ),
          ),
          if (isDone) ...[
            const SizedBox(width: 6),
            const Icon(Icons.check_circle_rounded,
                size: 14, color: AppColors.healthPrimary),
          ] else if (isMoved) ...[
            const SizedBox(width: 6),
            const Icon(Icons.arrow_forward_rounded,
                size: 14, color: AppColors.errandPrimary),
          ],
        ],
      ),
    );
  }

  Widget _buildWeekProgress() {
    final total = _doneTasks + _movedTasks + _pendingTasks;
    if (total == 0) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'WEEK PROGRESS',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: AppColors.sectionTitle,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: SizedBox(
            height: 10,
            child: Row(
              children: [
                if (_doneTasks > 0)
                  Flexible(
                    flex: (_doneTasks * 1000).round(),
                    child: Container(color: AppColors.healthPrimary),
                  ),
                if (_movedTasks > 0)
                  Flexible(
                    flex: (_movedTasks * 1000).round(),
                    child: Container(color: AppColors.errandPrimary),
                  ),
                if (_pendingTasks > 0)
                  Flexible(
                    flex: (_pendingTasks * 1000).round(),
                    child: Container(color: AppColors.glassBorder),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildProgressLegend(
                AppColors.healthPrimary, '$_doneTasks done'),
            const SizedBox(width: 16),
            _buildProgressLegend(
                AppColors.errandPrimary, '$_movedTasks moved'),
            const SizedBox(width: 16),
            _buildProgressLegend(
                AppColors.textMuted, '$_pendingTasks upcoming'),
          ],
        ),
      ],
    );
  }

  Widget _buildProgressLegend(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11.5,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}
