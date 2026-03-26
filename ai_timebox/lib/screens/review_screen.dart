import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../models/day_review.dart';
import '../models/enums.dart';
import '../models/task.dart';
import '../services/llm_service.dart';
import '../main.dart' show db;
import '../theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/task_check_item.dart';

class ReviewScreen extends StatefulWidget {
  const ReviewScreen({super.key});

  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen> {
  final _llm = LlmService();

  // Data
  List<Task> _tasks = [];
  List<Task> _droppedTasks = [];
  int _streakDays = 1;
  bool _hasHealthToday = false;
  bool _loading = true;
  bool _saving = false;

  // LLM insight
  String? _dailyInsight;
  String? _healthInsight;
  bool _insightLoading = false;

  // Track which undone tasks have been acted on
  final Set<String> _actedOn = {};

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _loadData();
  }

  Future<void> _loadData() async {
    final today = _today();
    final yesterday = today.subtract(const Duration(days: 1));

    final tasks = await db.getTasksForDate(today);
    final dropped = await db.getDroppedTasks();

    // Check if there's a health log today
    final weekLogs = await db.getHealthLogsForWeek(
      today.subtract(Duration(days: today.weekday - 1)),
    );
    final hasHealthToday = weekLogs.any((log) {
      final logDay = DateTime(log.date.year, log.date.month, log.date.day);
      return logDay == today;
    });

    // Compute streak
    final yesterdayReview = await db.getDayReview(yesterday);
    final streak =
        yesterdayReview != null ? yesterdayReview.streakDay + 1 : 1;

    if (!mounted) return;
    setState(() {
      _tasks = tasks;
      _droppedTasks = dropped;
      _hasHealthToday = hasHealthToday;
      _streakDays = streak;
      _loading = false;
    });

    // Kick off LLM insights in background
    _loadInsights(tasks, weekLogs.length, streak);
  }

  Future<void> _loadInsights(
      List<Task> tasks, int healthActivities, int streak) async {
    final done = tasks.where((t) => t.status == TaskStatus.done).toList();
    final undone = tasks
        .where((t) =>
            t.status != TaskStatus.done && t.status != TaskStatus.dropped)
        .toList();

    setState(() => _insightLoading = true);
    try {
      final result = await _llm.generateInsights(
        completedCount: done.length,
        totalCount: tasks.length,
        undoneTasks: undone,
        healthActivitiesThisWeek: healthActivities,
        streakDays: streak,
      );
      if (!mounted) return;
      setState(() {
        _dailyInsight = result?['daily_insight'] as String?;
        _healthInsight = result?['health_insight'] as String?;
      });
    } finally {
      if (mounted) setState(() => _insightLoading = false);
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  DateTime _today() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }

  String _dateSubtitle() {
    final now = DateTime.now();
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    const days = [
      'Monday', 'Tuesday', 'Wednesday', 'Thursday',
      'Friday', 'Saturday', 'Sunday'
    ];
    return '${days[now.weekday - 1]}, ${months[now.month - 1]} ${now.day}';
  }

  int get _completedCount =>
      _tasks.where((t) => t.status == TaskStatus.done).length;

  List<Task> get _undoneTasks => _tasks
      .where((t) =>
          t.status != TaskStatus.done && t.status != TaskStatus.dropped)
      .toList();

  // ── Save review ───────────────────────────────────────────────────────────

  Future<void> _saveAndClose() async {
    if (_saving) return;
    setState(() => _saving = true);

    try {
      final review = DayReview(
        id: const Uuid().v4(),
        date: _today(),
        completedCount: _completedCount,
        totalCount: _tasks.length,
        streakDay: _streakDays,
      );
      await db.saveDayReview(review);
      if (mounted) Navigator.of(context).pop();
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  // ── Undone task actions ───────────────────────────────────────────────────

  Future<void> _moveToTomorrow(Task task) async {
    final tomorrow = _today().add(const Duration(days: 1));
    await db.moveTask(task.id, tomorrow);
    _reloadTasks();
    setState(() => _actedOn.add(task.id));
  }

  Future<void> _letItGo(Task task) async {
    await db.updateTaskStatus(task.id, TaskStatus.dropped);
    _reloadTasks();
    setState(() => _actedOn.add(task.id));
  }

  Future<void> _pickDay(Task task) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _today().add(const Duration(days: 1)),
      firstDate: _today(),
      lastDate: _today().add(const Duration(days: 90)),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppColors.workPrimary,
            surface: AppColors.surface,
            onSurface: AppColors.textPrimary,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      await db.moveTask(task.id, picked);
      _reloadTasks();
      setState(() => _actedOn.add(task.id));
    }
  }

  Future<void> _lockItIn(Task task) async {
    // V1: just move to tomorrow
    final tomorrow = _today().add(const Duration(days: 1));
    await db.moveTask(task.id, tomorrow);
    _reloadTasks();
    setState(() => _actedOn.add(task.id));
  }

  Future<void> _reloadTasks() async {
    final tasks = await db.getTasksForDate(_today());
    final dropped = await db.getDroppedTasks();
    if (!mounted) return;
    setState(() {
      _tasks = tasks;
      _droppedTasks = dropped;
    });
  }

  Future<void> _reviveTask(Task task) async {
    await db.updateTaskStatus(task.id, TaskStatus.pending);
    // We also need to set the scheduled_date to today; use moveTask so
    // scheduled_date is updated, but avoid incrementing times_moved by
    // directly updating. Since we don't have a direct "reschedule without
    // increment", we use moveTask and accept the +1 — acceptable for revives.
    await db.moveTask(task.id, _today());
    final dropped = await db.getDroppedTasks();
    final tasks = await db.getTasksForDate(_today());
    if (!mounted) return;
    setState(() {
      _droppedTasks = dropped;
      _tasks = tasks;
    });
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: _loading
            ? const Center(
                child:
                    CircularProgressIndicator(color: AppColors.workPrimary),
              )
            : Column(
                children: [
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                      children: [
                        _buildHeader(),
                        const SizedBox(height: 20),
                        _buildTaskChecklist(),
                        if (_undoneTasks.isNotEmpty) ...[
                          const SizedBox(height: 20),
                          _buildUndoneSection(),
                        ],
                        const SizedBox(height: 20),
                        _buildStatsRow(),
                        const SizedBox(height: 20),
                        _buildInsightSection(),
                        const SizedBox(height: 20),
                        _buildArchivedLink(),
                      ],
                    ),
                  ),
                  _buildDoneButton(),
                ],
              ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'How did it go?',
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _dateSubtitle(),
          style: const TextStyle(
            fontSize: 14,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskChecklist() {
    if (_tasks.isEmpty) {
      return GlassCard(
        child: const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'No tasks today.',
            style: TextStyle(fontSize: 13.5, color: AppColors.textMuted),
          ),
        ),
      );
    }

    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        children: _tasks
            .map((t) => TaskCheckItem(
                  title: t.title,
                  isDone: t.status == TaskStatus.done,
                  onTap: () {},
                ))
            .toList(),
      ),
    );
  }

  Widget _buildUndoneSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'STILL ON YOUR PLATE',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: AppColors.sectionTitle,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),
        ..._undoneTasks.map((t) => _buildUndoneCard(t)),
      ],
    );
  }

  Widget _buildUndoneCard(Task task) {
    if (_actedOn.contains(task.id)) return const SizedBox.shrink();

    final times = task.timesMoved;
    String message;
    List<Widget> actions;

    if (times == 0) {
      message = "Didn't happen. That's okay.";
      actions = [
        _ActionButton(
          label: 'Move to tomorrow',
          color: AppColors.workPrimary,
          onTap: () => _moveToTomorrow(task),
        ),
        _ActionButton(
          label: 'Let it go',
          color: AppColors.textMuted,
          onTap: () => _letItGo(task),
        ),
      ];
    } else if (times == 1) {
      message = 'Slipped twice. Still want to do it?';
      actions = [
        _ActionButton(
          label: 'Pick a day',
          color: AppColors.workPrimary,
          onTap: () => _pickDay(task),
        ),
        _ActionButton(
          label: 'Let it go',
          color: AppColors.textMuted,
          onTap: () => _letItGo(task),
        ),
      ];
    } else {
      final daysLabel = '${times + 1} days';
      message = "Been on your list $daysLabel. Timing isn't right.";
      actions = [
        _ActionButton(
          label: 'Lock it in',
          color: AppColors.workPrimary,
          onTap: () => _lockItIn(task),
        ),
        _ActionButton(
          label: 'Archive',
          color: AppColors.socialPrimary,
          onTap: () => _letItGo(task),
        ),
      ];
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: GlassCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              task.title,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              style: const TextStyle(
                fontSize: 12.5,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: actions
                  .map((a) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: a,
                      ))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsRow() {
    return Row(
      children: [
        Expanded(
          child: _StatCard(
            label: 'Done',
            value: '$_completedCount / ${_tasks.length}',
            icon: Icons.check_circle_outline_rounded,
            iconColor: AppColors.healthPrimary,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatCard(
            label: 'Health',
            value: _hasHealthToday ? 'Active' : 'Rest',
            icon: _hasHealthToday
                ? Icons.directions_walk_rounded
                : Icons.hotel_rounded,
            iconColor: _hasHealthToday
                ? AppColors.healthPrimary
                : AppColors.textMuted,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatCard(
            label: 'Streak',
            value: 'Day $_streakDays',
            icon: Icons.local_fire_department_rounded,
            iconColor: AppColors.errandPrimary,
          ),
        ),
      ],
    );
  }

  Widget _buildInsightSection() {
    if (_insightLoading) {
      return GlassCard(
        child: const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Row(
            children: [
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  color: AppColors.workPrimary,
                  strokeWidth: 2,
                ),
              ),
              SizedBox(width: 10),
              Text(
                'Getting your reflection...',
                style: TextStyle(
                    fontSize: 13, color: AppColors.textMuted),
              ),
            ],
          ),
        ),
      );
    }

    if (_dailyInsight == null && _healthInsight == null) {
      return const SizedBox.shrink();
    }

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'REFLECTION',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.sectionTitle,
              letterSpacing: 0.8,
            ),
          ),
          if (_dailyInsight != null) ...[
            const SizedBox(height: 10),
            Text(
              _dailyInsight!,
              style: const TextStyle(
                fontSize: 13.5,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
            ),
          ],
          if (_healthInsight != null) ...[
            const SizedBox(height: 10),
            Text(
              _healthInsight!,
              style: const TextStyle(
                fontSize: 12.5,
                color: AppColors.textMuted,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildArchivedLink() {
    if (_droppedTasks.isEmpty) return const SizedBox.shrink();

    return GestureDetector(
      onTap: _showArchivedSheet,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Text(
          'View ${_droppedTasks.length} archived task${_droppedTasks.length == 1 ? '' : 's'}',
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppColors.workPrimary,
          ),
        ),
      ),
    );
  }

  void _showArchivedSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Archived tasks',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed: () => Navigator.pop(ctx),
                          icon: const Icon(Icons.close_rounded,
                              color: AppColors.textMuted, size: 20),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    if (_droppedTasks.isEmpty)
                      const Text(
                        'No archived tasks.',
                        style: TextStyle(
                            fontSize: 13.5, color: AppColors.textMuted),
                      )
                    else
                      ..._droppedTasks.map((t) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    t.title,
                                    style: const TextStyle(
                                      fontSize: 13.5,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                GestureDetector(
                                  onTap: () async {
                                    Navigator.pop(ctx);
                                    await _reviveTask(t);
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: AppColors.workBg,
                                      borderRadius:
                                          BorderRadius.circular(8),
                                    ),
                                    child: const Text(
                                      'Revive',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.workPrimary,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          )),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildDoneButton() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
      child: GestureDetector(
        onTap: _saving ? null : _saveAndClose,
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
            child: _saving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 2,
                    ),
                  )
                : const Text(
                    'Done with today',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}

// ── Reusable widgets ─────────────────────────────────────────────────────────

class _ActionButton extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionButton({
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color iconColor;

  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      child: Column(
        children: [
          Icon(icon, size: 20, color: iconColor),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              fontSize: 10.5,
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}
