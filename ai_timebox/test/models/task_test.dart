import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/task.dart';

void main() {
  group('Task', () {
    test('creates with defaults', () {
      final task = Task(
        id: 'abc',
        title: 'Write tests',
        pillar: Pillar.work,
        estimatedMinutes: 30,
        taskType: TaskType.deepFocus,
        createdAt: DateTime(2026, 3, 26),
        scheduledDate: DateTime(2026, 3, 26),
      );

      expect(task.id, 'abc');
      expect(task.title, 'Write tests');
      expect(task.pillar, Pillar.work);
      expect(task.estimatedMinutes, 30);
      expect(task.taskType, TaskType.deepFocus);
      expect(task.status, TaskStatus.pending);
      expect(task.timesMoved, 0);
      expect(task.scheduledTime, isNull);
    });

    test('toMap / fromMap roundtrip', () {
      final original = Task(
        id: 'xyz',
        title: 'Go for a run',
        pillar: Pillar.health,
        estimatedMinutes: 45,
        taskType: TaskType.outing,
        status: TaskStatus.done,
        createdAt: DateTime(2026, 3, 26, 8, 0),
        scheduledDate: DateTime(2026, 3, 26),
        scheduledTime: '08:00',
        timesMoved: 2,
      );

      final map = original.toMap();
      final restored = Task.fromMap(map);

      expect(restored.id, original.id);
      expect(restored.title, original.title);
      expect(restored.pillar, original.pillar);
      expect(restored.estimatedMinutes, original.estimatedMinutes);
      expect(restored.taskType, original.taskType);
      expect(restored.status, original.status);
      expect(restored.createdAt, original.createdAt);
      expect(restored.scheduledDate, original.scheduledDate);
      expect(restored.scheduledTime, original.scheduledTime);
      expect(restored.timesMoved, original.timesMoved);
    });

    test('copyWith preserves unchanged fields', () {
      final original = Task(
        id: 'id1',
        title: 'Call dentist',
        pillar: Pillar.errand,
        estimatedMinutes: 15,
        taskType: TaskType.call,
        createdAt: DateTime(2026, 3, 26),
        scheduledDate: DateTime(2026, 3, 26),
      );

      final updated = original.copyWith(status: TaskStatus.moved, timesMoved: 1);

      expect(updated.id, original.id);
      expect(updated.title, original.title);
      expect(updated.pillar, original.pillar);
      expect(updated.status, TaskStatus.moved);
      expect(updated.timesMoved, 1);
    });

    test('toMap stores status as string name', () {
      final task = Task(
        id: 't1',
        title: 'Test',
        pillar: Pillar.social,
        estimatedMinutes: 20,
        taskType: TaskType.quick,
        createdAt: DateTime(2026, 3, 26),
        scheduledDate: DateTime(2026, 3, 26),
      );
      final map = task.toMap();
      expect(map['status'], 'pending');
      expect(map['pillar'], 'social');
      expect(map['task_type'], 'quick');
    });
  });
}
