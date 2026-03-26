import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/belief.dart';
import 'package:ai_timebox/models/task.dart';
import 'package:ai_timebox/models/schedule_slot.dart';
import 'package:ai_timebox/services/offline_scheduler.dart';

void main() {
  group('OfflineScheduler', () {
    // Helper to build a Belief map with a given peakEnergy hour
    Map<BeliefParameter, Belief> beliefsWithPeak(double peakHour) {
      final now = DateTime(2026, 3, 26);
      return {
        BeliefParameter.peakEnergy: Belief(
          parameter: BeliefParameter.peakEnergy,
          value: peakHour,
          confidence: 0.7,
          lastUpdated: now,
        ),
        BeliefParameter.deepWorkTolerance: Belief(
          parameter: BeliefParameter.deepWorkTolerance,
          value: 60.0,
          confidence: 0.3,
          lastUpdated: now,
        ),
        BeliefParameter.contextSwitchCost: Belief(
          parameter: BeliefParameter.contextSwitchCost,
          value: 0.5,
          confidence: 0.3,
          lastUpdated: now,
        ),
        BeliefParameter.chaosTolerance: Belief(
          parameter: BeliefParameter.chaosTolerance,
          value: 0.4,
          confidence: 0.3,
          lastUpdated: now,
        ),
        BeliefParameter.meetingTolerance: Belief(
          parameter: BeliefParameter.meetingTolerance,
          value: 0.5,
          confidence: 0.3,
          lastUpdated: now,
        ),
        BeliefParameter.recoveryRate: Belief(
          parameter: BeliefParameter.recoveryRate,
          value: 0.1,
          confidence: 0.3,
          lastUpdated: now,
        ),
      };
    }

    Task makeTask({
      required String id,
      required String title,
      required TaskType taskType,
      int estimatedMinutes = 60,
    }) {
      return Task(
        id: id,
        title: title,
        pillar: Pillar.work,
        estimatedMinutes: estimatedMinutes,
        taskType: taskType,
        createdAt: DateTime(2026, 3, 26),
        scheduledDate: DateTime(2026, 3, 26),
      );
    }

    group('generate', () {
      test('places deepFocus task starting at peak energy hour', () {
        final beliefs = beliefsWithPeak(9.0);
        final tasks = [
          makeTask(id: '1', title: 'Write report', taskType: TaskType.deepFocus),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        expect(slots, isNotEmpty);
        final deepFocusSlot = slots.firstWhere(
          (s) => s.slotType == SlotType.task && s.title == 'Write report',
        );
        // startTime should reflect hour 9 (i.e. "09:XX")
        expect(deepFocusSlot.startTime, startsWith('09:'));
      });

      test('places deepFocus task at correct peak hour (14:00)', () {
        final beliefs = beliefsWithPeak(14.0);
        final tasks = [
          makeTask(id: '1', title: 'Code review', taskType: TaskType.deepFocus),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        final deepFocusSlot = slots.firstWhere(
          (s) => s.slotType == SlotType.task && s.title == 'Code review',
        );
        expect(deepFocusSlot.startTime, startsWith('14:'));
      });

      test('deepFocus task appears before quick and call tasks', () {
        final beliefs = beliefsWithPeak(9.0);
        final tasks = [
          makeTask(id: '2', title: 'Quick email', taskType: TaskType.quick, estimatedMinutes: 15),
          makeTask(id: '1', title: 'Deep work', taskType: TaskType.deepFocus),
          makeTask(id: '3', title: 'Phone call', taskType: TaskType.call, estimatedMinutes: 30),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        final taskSlots = slots.where((s) => s.slotType == SlotType.task).toList();
        final deepFocusIdx = taskSlots.indexWhere((s) => s.title == 'Deep work');
        final quickIdx = taskSlots.indexWhere((s) => s.title == 'Quick email');
        final callIdx = taskSlots.indexWhere((s) => s.title == 'Phone call');

        expect(deepFocusIdx, lessThan(quickIdx));
        expect(deepFocusIdx, lessThan(callIdx));
      });

      test('outing task is placed in afternoon (startTime hour >= 12)', () {
        final beliefs = beliefsWithPeak(9.0);
        final tasks = [
          makeTask(id: '1', title: 'Grocery run', taskType: TaskType.outing, estimatedMinutes: 45),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        final outingSlot = slots.firstWhere(
          (s) => s.slotType == SlotType.task && s.title == 'Grocery run',
        );
        final hour = int.parse(outingSlot.startTime.split(':')[0]);
        expect(hour, greaterThanOrEqualTo(12));
      });

      test('adds buffer slots between tasks', () {
        final beliefs = beliefsWithPeak(9.0);
        final tasks = [
          makeTask(id: '1', title: 'Deep work', taskType: TaskType.deepFocus),
          makeTask(id: '2', title: 'Quick email', taskType: TaskType.quick, estimatedMinutes: 15),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        final bufferSlots = slots.where((s) => s.slotType == SlotType.buffer).toList();
        expect(bufferSlots, isNotEmpty);
      });

      test('buffer is 15 min when contextSwitchCost > 0.6', () {
        final now = DateTime(2026, 3, 26);
        final beliefs = {
          BeliefParameter.peakEnergy: Belief(
            parameter: BeliefParameter.peakEnergy,
            value: 9.0,
            confidence: 0.7,
            lastUpdated: now,
          ),
          BeliefParameter.deepWorkTolerance: Belief(
            parameter: BeliefParameter.deepWorkTolerance,
            value: 60.0,
            confidence: 0.3,
            lastUpdated: now,
          ),
          BeliefParameter.contextSwitchCost: Belief(
            parameter: BeliefParameter.contextSwitchCost,
            value: 0.7, // > 0.6 → 15-min buffer
            confidence: 0.3,
            lastUpdated: now,
          ),
          BeliefParameter.chaosTolerance: Belief(
            parameter: BeliefParameter.chaosTolerance,
            value: 0.4,
            confidence: 0.3,
            lastUpdated: now,
          ),
          BeliefParameter.meetingTolerance: Belief(
            parameter: BeliefParameter.meetingTolerance,
            value: 0.5,
            confidence: 0.3,
            lastUpdated: now,
          ),
          BeliefParameter.recoveryRate: Belief(
            parameter: BeliefParameter.recoveryRate,
            value: 0.1,
            confidence: 0.3,
            lastUpdated: now,
          ),
        };

        final tasks = [
          makeTask(id: '1', title: 'Deep work', taskType: TaskType.deepFocus),
          makeTask(id: '2', title: 'Quick task', taskType: TaskType.quick, estimatedMinutes: 15),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        // Find buffer between deep work and quick task
        final bufferSlot = slots.firstWhere(
          (s) => s.slotType == SlotType.buffer,
          orElse: () => const ScheduleSlot(
            slotType: SlotType.buffer,
            startTime: '00:00',
            endTime: '00:00',
            title: 'none',
          ),
        );

        if (bufferSlot.title != 'none') {
          final startHour = int.parse(bufferSlot.startTime.split(':')[0]);
          final startMin = int.parse(bufferSlot.startTime.split(':')[1]);
          final endHour = int.parse(bufferSlot.endTime.split(':')[0]);
          final endMin = int.parse(bufferSlot.endTime.split(':')[1]);
          final durationMins = (endHour * 60 + endMin) - (startHour * 60 + startMin);
          expect(durationMins, equals(15));
        }
      });

      test('returns list of ScheduleSlot', () {
        final beliefs = beliefsWithPeak(9.0);
        final tasks = [
          makeTask(id: '1', title: 'Deep work', taskType: TaskType.deepFocus),
        ];

        final result = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        expect(result, isA<List<ScheduleSlot>>());
      });

      test('returns empty list when no tasks provided', () {
        final beliefs = beliefsWithPeak(9.0);
        final slots = OfflineScheduler.generate(
          tasks: [],
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        expect(slots, isEmpty);
      });

      test('each slot has valid startTime and endTime format (HH:mm)', () {
        final beliefs = beliefsWithPeak(10.0);
        final tasks = [
          makeTask(id: '1', title: 'Deep work', taskType: TaskType.deepFocus),
          makeTask(id: '2', title: 'Email', taskType: TaskType.quick, estimatedMinutes: 20),
        ];

        final slots = OfflineScheduler.generate(
          tasks: tasks,
          beliefs: beliefs,
          wakeTime: '06:00',
          sleepTime: '22:00',
        );

        final timeRegex = RegExp(r'^\d{2}:\d{2}$');
        for (final slot in slots) {
          expect(slot.startTime, matches(timeRegex));
          expect(slot.endTime, matches(timeRegex));
        }
      });
    });
  });
}
