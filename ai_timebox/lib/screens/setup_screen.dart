import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../models/week_config.dart';
import '../services/belief_engine.dart';
import '../storage/local_db.dart';
import '../theme.dart';
import '../widgets/glass_card.dart';

// ---------------------------------------------------------------------------
// SetupScreen
// ---------------------------------------------------------------------------

class SetupScreen extends StatefulWidget {
  final bool isUpdate;

  const SetupScreen({super.key, this.isUpdate = false});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  // Step 1: teaching day selection
  // teachingDays stores weekday integers 1=Mon … 7=Sun (ISO weekday)
  final Set<int> _teachingDays = {};

  // Step 2: wake / sleep time
  Duration _wakeTime = const Duration(hours: 7);   // 07:00
  Duration _sleepTime = const Duration(hours: 23);  // 23:00

  // Which step is visible (0 = day picker, 1 = time picker)
  int _step = 0;

  bool _saving = false;

  // Old config, populated when isUpdate=true
  WeekConfig? _oldConfig;

  // Day labels (Mon-Sun)
  static const List<String> _dayLabels = [
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.isUpdate) {
      _loadExistingConfig();
    }
  }

  Future<void> _loadExistingConfig() async {
    final db = LocalDb();
    await db.init();
    final config = await db.getLatestWeekConfig();
    await db.close();

    if (config != null && mounted) {
      setState(() {
        _oldConfig = config;
        _teachingDays
          ..clear()
          ..addAll(config.teachingDays);

        // Parse existing times
        final wakeParts = config.wakeTime.split(':');
        _wakeTime = Duration(
          hours: int.parse(wakeParts[0]),
          minutes: int.parse(wakeParts[1]),
        );
        final sleepParts = config.sleepTime.split(':');
        _sleepTime = Duration(
          hours: int.parse(sleepParts[0]),
          minutes: int.parse(sleepParts[1]),
        );
      });
    }
  }

  void _toggleDay(int isoWeekday) {
    setState(() {
      if (_teachingDays.contains(isoWeekday)) {
        _teachingDays.remove(isoWeekday);
      } else {
        _teachingDays.add(isoWeekday);
      }
    });
  }

  String _durationToTimeString(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    return '$h:$m';
  }

  Future<void> _onNext() async {
    // Step 0 → step 1 (only when not isUpdate)
    if (_step == 0 && !widget.isUpdate) {
      setState(() => _step = 1);
      return;
    }

    // Otherwise save
    await _save();
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() => _saving = true);

    try {
      final db = LocalDb();
      await db.init();

      final now = DateTime.now();
      // Week start = most recent Monday
      final weekday = now.weekday; // 1=Mon
      final weekStart = now.subtract(Duration(days: weekday - 1));
      final weekStartDay =
          DateTime(weekStart.year, weekStart.month, weekStart.day);

      final config = WeekConfig(
        id: const Uuid().v4(),
        weekStartDate: weekStartDay,
        teachingDays: _teachingDays.toList()..sort(),
        wakeTime: _durationToTimeString(_wakeTime),
        sleepTime: _durationToTimeString(_sleepTime),
      );

      await db.saveWeekConfig(config);

      // First launch: seed default beliefs
      if (!widget.isUpdate) {
        final engine = BeliefEngine();
        final defaults = engine.getDefaultBeliefs();
        for (final belief in defaults.values) {
          await db.saveBelief(belief);
        }
      }

      // Update mode: check for free→teaching day changes
      if (widget.isUpdate && _oldConfig != null) {
        final oldTeaching = Set<int>.from(_oldConfig!.teachingDays);
        final newTeaching = Set<int>.from(_teachingDays);
        final gainedTeaching =
            newTeaching.difference(oldTeaching).toList()..sort();

        if (gainedTeaching.isNotEmpty && mounted) {
          for (final dayIndex in gainedTeaching) {
            // dayIndex is ISO weekday (1=Mon..7=Sun)
            // Find the next occurrence of this weekday in the current week
            final dayDate = _dateForIsoWeekday(weekStartDay, dayIndex);
            final tasks = await db.getTasksForDate(dayDate);

            if (tasks.isNotEmpty && mounted) {
              final dayLabel = _dayLabels[dayIndex - 1];
              final confirmed = await _showMoveDialog(dayLabel, tasks.length);
              if (confirmed == true) {
                // Move tasks to the following week's same day
                final nextWeekDate =
                    dayDate.add(const Duration(days: 7));
                for (final task in tasks) {
                  await db.moveTask(task.id, nextWeekDate);
                }
              }
            }
          }
        }
      }

      await db.close();

      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const _DailyScreenPlaceholder()),
          (_) => false,
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  DateTime _dateForIsoWeekday(DateTime weekStart, int isoWeekday) {
    return weekStart.add(Duration(days: isoWeekday - 1));
  }

  Future<bool?> _showMoveDialog(String dayLabel, int taskCount) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: Text(
          '$dayLabel is now a teaching day',
          style: const TextStyle(color: AppColors.textPrimary),
        ),
        content: Text(
          'You have $taskCount task${taskCount == 1 ? '' : 's'} on $dayLabel. Move ${taskCount == 1 ? 'it' : 'them'} to next week?',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text(
              'Keep',
              style: TextStyle(color: AppColors.textMuted),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text(
              'Move',
              style: TextStyle(color: AppColors.workPrimary),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 56),
              _buildHeader(),
              const SizedBox(height: 32),
              if (_step == 0) _buildDayPicker(),
              if (_step == 1) _buildTimePickers(),
              const Spacer(),
              _buildNextButton(),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final title =
        widget.isUpdate ? 'Update your week' : 'Your week';
    final subtitle = _step == 0
        ? (widget.isUpdate
            ? 'You can update this every week.'
            : 'Tap your teaching days')
        : 'So we know your available hours';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: const TextStyle(
            fontSize: 16,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Step 1: Day picker
  // ---------------------------------------------------------------------------

  Widget _buildDayPicker() {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(7, (i) {
          final isoWeekday = i + 1; // 1=Mon..7=Sun
          final isSelected = _teachingDays.contains(isoWeekday);
          return _SetupDayPill(
            label: _dayLabels[i],
            isSelected: isSelected,
            onTap: () => _toggleDay(isoWeekday),
          );
        }),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 2: Time pickers
  // ---------------------------------------------------------------------------

  Widget _buildTimePickers() {
    return Column(
      children: [
        GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Wake up',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 120,
                child: CupertinoTimerPicker(
                  mode: CupertinoTimerPickerMode.hm,
                  initialTimerDuration: _wakeTime,
                  backgroundColor: Colors.transparent,
                  onTimerDurationChanged: (d) =>
                      setState(() => _wakeTime = d),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Sleep',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 120,
                child: CupertinoTimerPicker(
                  mode: CupertinoTimerPickerMode.hm,
                  initialTimerDuration: _sleepTime,
                  backgroundColor: Colors.transparent,
                  onTimerDurationChanged: (d) =>
                      setState(() => _sleepTime = d),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Next / Done button
  // ---------------------------------------------------------------------------

  Widget _buildNextButton() {
    final isLastStep = widget.isUpdate || _step == 1;
    final label = isLastStep ? 'Done' : 'Next';

    return Center(
      child: GestureDetector(
        onTap: _saving ? null : _onNext,
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
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 2,
                    ),
                  )
                : Text(
                    label,
                    style: const TextStyle(
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

// ---------------------------------------------------------------------------
// Private: simplified day pill for setup (no task count / day number needed)
// ---------------------------------------------------------------------------

class _SetupDayPill extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _SetupDayPill({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: 36,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0x1F6366F1) // indigo tinted
              : const Color(0x08FFFFFF),
          borderRadius: BorderRadius.circular(10),
          border: isSelected
              ? Border.all(color: const Color(0xFF6366F1), width: 1.5)
              : null,
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: isSelected
                  ? const Color(0xFF818CF8)
                  : AppColors.textMuted,
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Daily screen placeholder (used until Task 11 is built)
// ---------------------------------------------------------------------------

class _DailyScreenPlaceholder extends StatelessWidget {
  const _DailyScreenPlaceholder();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Text(
          'Daily Screen',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
