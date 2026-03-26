import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/schedule_slot.dart';

void main() {
  group('ScheduleSlot', () {
    test('fromJson maps snake_case slot_type correctly', () {
      final json = {
        'task_id': 'abc',
        'slot_type': 'task',
        'start_time': '09:00',
        'end_time': '09:30',
        'title': 'Deep work block',
        'pillar': 'work',
      };

      final slot = ScheduleSlot.fromJson(json);

      expect(slot.taskId, 'abc');
      expect(slot.slotType, SlotType.task);
      expect(slot.startTime, '09:00');
      expect(slot.endTime, '09:30');
      expect(slot.title, 'Deep work block');
      expect(slot.pillar, Pillar.work);
    });

    test('fromJson maps health_nudge to healthNudge', () {
      final json = {
        'task_id': null,
        'slot_type': 'health_nudge',
        'start_time': '11:00',
        'end_time': '11:10',
        'title': 'Stretch break',
        'pillar': null,
      };

      final slot = ScheduleSlot.fromJson(json);

      expect(slot.slotType, SlotType.healthNudge);
      expect(slot.taskId, isNull);
      expect(slot.pillar, isNull);
    });

    test('fromJson maps buffer slot_type', () {
      final json = {
        'task_id': null,
        'slot_type': 'buffer',
        'start_time': '12:00',
        'end_time': '12:15',
        'title': 'Buffer',
        'pillar': null,
      };

      final slot = ScheduleSlot.fromJson(json);
      expect(slot.slotType, SlotType.buffer);
    });

    test('fromJson maps open slot_type', () {
      final json = {
        'task_id': null,
        'slot_type': 'open',
        'start_time': '15:00',
        'end_time': '15:30',
        'title': 'Free time',
        'pillar': null,
      };

      final slot = ScheduleSlot.fromJson(json);
      expect(slot.slotType, SlotType.open);
    });

    test('fromJson handles all pillar values', () {
      for (final pillarStr in ['work', 'health', 'errand', 'social']) {
        final json = {
          'task_id': null,
          'slot_type': 'task',
          'start_time': '10:00',
          'end_time': '10:30',
          'title': 'Test',
          'pillar': pillarStr,
        };
        final slot = ScheduleSlot.fromJson(json);
        expect(slot.pillar, isNotNull);
      }
    });
  });
}
