import '../models/belief.dart';
import '../models/enums.dart';
import '../models/schedule_slot.dart';
import '../models/task.dart';

class OfflineScheduler {
  /// Generates a list of ScheduleSlots from the given tasks and beliefs.
  ///
  /// Sorting order: deepFocus → quick/call → outing
  /// - deepFocus tasks start at the peakEnergy belief hour
  /// - Outings are placed in the afternoon (>= 12:00)
  /// - Buffers between tasks: 15 min if contextSwitchCost > 0.6,
  ///   10 min if > 0.3, else 5 min
  static List<ScheduleSlot> generate({
    required List<Task> tasks,
    required Map<BeliefParameter, Belief> beliefs,
    required String wakeTime,
    required String sleepTime,
  }) {
    if (tasks.isEmpty) return [];

    final peakHour = beliefs[BeliefParameter.peakEnergy]?.value ?? 10.0;
    final contextSwitchCost =
        beliefs[BeliefParameter.contextSwitchCost]?.value ?? 0.5;

    final bufferMinutes = contextSwitchCost > 0.6
        ? 15
        : contextSwitchCost > 0.3
            ? 10
            : 5;

    // Sort: deepFocus first, then quick/call, then outing
    final sorted = List<Task>.from(tasks)
      ..sort((a, b) => _taskPriority(a.taskType).compareTo(_taskPriority(b.taskType)));

    final slots = <ScheduleSlot>[];

    // deepFocus tasks start at peakEnergy hour
    int currentMinutes = _hourToMinutes(peakHour.floor());

    // Afternoon start for outings (13:00 by default)
    const afternoonMinutes = 13 * 60;

    final deepFocusTasks = sorted.where((t) => t.taskType == TaskType.deepFocus).toList();
    final midTasks = sorted
        .where((t) => t.taskType == TaskType.quick || t.taskType == TaskType.call)
        .toList();
    final outingTasks = sorted.where((t) => t.taskType == TaskType.outing).toList();

    bool firstSlot = true;

    // Place deepFocus tasks starting at peak hour
    for (final task in deepFocusTasks) {
      if (!firstSlot) {
        // Add buffer before this task
        final bufferStart = currentMinutes;
        final bufferEnd = currentMinutes + bufferMinutes;
        slots.add(ScheduleSlot(
          slotType: SlotType.buffer,
          startTime: _minutesToTime(bufferStart),
          endTime: _minutesToTime(bufferEnd),
          title: 'Buffer',
        ));
        currentMinutes = bufferEnd;
      }
      firstSlot = false;

      final endMinutes = currentMinutes + task.estimatedMinutes;
      slots.add(ScheduleSlot(
        taskId: task.id,
        slotType: SlotType.task,
        startTime: _minutesToTime(currentMinutes),
        endTime: _minutesToTime(endMinutes),
        title: task.title,
        pillar: task.pillar,
      ));
      currentMinutes = endMinutes;
    }

    // Place quick/call tasks after deep focus
    for (final task in midTasks) {
      if (!firstSlot) {
        final bufferStart = currentMinutes;
        final bufferEnd = currentMinutes + bufferMinutes;
        slots.add(ScheduleSlot(
          slotType: SlotType.buffer,
          startTime: _minutesToTime(bufferStart),
          endTime: _minutesToTime(bufferEnd),
          title: 'Buffer',
        ));
        currentMinutes = bufferEnd;
      }
      firstSlot = false;

      final endMinutes = currentMinutes + task.estimatedMinutes;
      slots.add(ScheduleSlot(
        taskId: task.id,
        slotType: SlotType.task,
        startTime: _minutesToTime(currentMinutes),
        endTime: _minutesToTime(endMinutes),
        title: task.title,
        pillar: task.pillar,
      ));
      currentMinutes = endMinutes;
    }

    // Place outing tasks in the afternoon
    int outingCursor = currentMinutes > afternoonMinutes ? currentMinutes : afternoonMinutes;
    for (final task in outingTasks) {
      if (slots.isNotEmpty) {
        final bufferStart = outingCursor;
        final bufferEnd = outingCursor + bufferMinutes;
        slots.add(ScheduleSlot(
          slotType: SlotType.buffer,
          startTime: _minutesToTime(bufferStart),
          endTime: _minutesToTime(bufferEnd),
          title: 'Buffer',
        ));
        outingCursor = bufferEnd;
      }

      final endMinutes = outingCursor + task.estimatedMinutes;
      slots.add(ScheduleSlot(
        taskId: task.id,
        slotType: SlotType.task,
        startTime: _minutesToTime(outingCursor),
        endTime: _minutesToTime(endMinutes),
        title: task.title,
        pillar: task.pillar,
      ));
      outingCursor = endMinutes;
    }

    return slots;
  }

  static int _taskPriority(TaskType type) {
    switch (type) {
      case TaskType.deepFocus:
        return 0;
      case TaskType.quick:
        return 1;
      case TaskType.call:
        return 1;
      case TaskType.outing:
        return 2;
    }
  }

  static int _hourToMinutes(int hour) => hour * 60;

  static String _minutesToTime(int totalMinutes) {
    final hours = (totalMinutes ~/ 60) % 24;
    final mins = totalMinutes % 60;
    return '${hours.toString().padLeft(2, '0')}:${mins.toString().padLeft(2, '0')}';
  }
}
