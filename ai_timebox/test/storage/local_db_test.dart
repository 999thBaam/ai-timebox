import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/task.dart';
import 'package:ai_timebox/models/belief.dart';
import 'package:ai_timebox/models/week_config.dart';
import 'package:ai_timebox/storage/local_db.dart';

void main() {
  sqfliteFfiInit();

  late LocalDb db;

  setUp(() async {
    db = LocalDb();
    await db.init(inMemory: true);
  });

  tearDown(() async {
    await db.close();
  });

  // ── Tasks ──────────────────────────────────────────────────────────────────

  group('Tasks', () {
    test('insert and retrieve task by date', () async {
      final date = DateTime(2026, 3, 26);
      final task = Task(
        id: 'task-1',
        title: 'Write unit tests',
        pillar: Pillar.work,
        estimatedMinutes: 60,
        taskType: TaskType.deepFocus,
        createdAt: DateTime(2026, 3, 26, 8, 0),
        scheduledDate: date,
      );

      await db.insertTask(task);
      final tasks = await db.getTasksForDate(date);

      expect(tasks.length, 1);
      expect(tasks.first.id, 'task-1');
      expect(tasks.first.title, 'Write unit tests');
      expect(tasks.first.pillar, Pillar.work);
      expect(tasks.first.estimatedMinutes, 60);
      expect(tasks.first.taskType, TaskType.deepFocus);
      expect(tasks.first.status, TaskStatus.pending);
      expect(tasks.first.timesMoved, 0);
    });

    test('getTasksForDate returns only tasks for that date', () async {
      final date1 = DateTime(2026, 3, 26);
      final date2 = DateTime(2026, 3, 27);

      final task1 = Task(
        id: 'task-a',
        title: 'Task on day 1',
        pillar: Pillar.work,
        estimatedMinutes: 30,
        taskType: TaskType.quick,
        createdAt: date1,
        scheduledDate: date1,
      );
      final task2 = Task(
        id: 'task-b',
        title: 'Task on day 2',
        pillar: Pillar.health,
        estimatedMinutes: 45,
        taskType: TaskType.outing,
        createdAt: date1,
        scheduledDate: date2,
      );

      await db.insertTask(task1);
      await db.insertTask(task2);

      final day1Tasks = await db.getTasksForDate(date1);
      final day2Tasks = await db.getTasksForDate(date2);

      expect(day1Tasks.length, 1);
      expect(day1Tasks.first.id, 'task-a');
      expect(day2Tasks.length, 1);
      expect(day2Tasks.first.id, 'task-b');
    });

    test('update task status', () async {
      final date = DateTime(2026, 3, 26);
      final task = Task(
        id: 'task-2',
        title: 'Morning run',
        pillar: Pillar.health,
        estimatedMinutes: 30,
        taskType: TaskType.outing,
        createdAt: date,
        scheduledDate: date,
      );

      await db.insertTask(task);
      await db.updateTaskStatus('task-2', TaskStatus.done);

      final tasks = await db.getTasksForDate(date);
      expect(tasks.first.status, TaskStatus.done);
    });

    test('move task updates date, increments times_moved, sets status=moved',
        () async {
      final originalDate = DateTime(2026, 3, 26);
      final newDate = DateTime(2026, 3, 27);

      final task = Task(
        id: 'task-3',
        title: 'Call dentist',
        pillar: Pillar.errand,
        estimatedMinutes: 15,
        taskType: TaskType.call,
        createdAt: originalDate,
        scheduledDate: originalDate,
        timesMoved: 0,
      );

      await db.insertTask(task);
      await db.moveTask('task-3', newDate);

      // Should no longer appear on original date
      final oldTasks = await db.getTasksForDate(originalDate);
      expect(oldTasks, isEmpty);

      // Should appear on new date with updated fields
      final newTasks = await db.getTasksForDate(newDate);
      expect(newTasks.length, 1);
      expect(newTasks.first.scheduledDate.year, newDate.year);
      expect(newTasks.first.scheduledDate.month, newDate.month);
      expect(newTasks.first.scheduledDate.day, newDate.day);
      expect(newTasks.first.timesMoved, 1);
      expect(newTasks.first.status, TaskStatus.moved);
    });

    test('move task increments times_moved cumulatively', () async {
      final date1 = DateTime(2026, 3, 26);
      final date2 = DateTime(2026, 3, 27);
      final date3 = DateTime(2026, 3, 28);

      final task = Task(
        id: 'task-move',
        title: 'Keep moving',
        pillar: Pillar.work,
        estimatedMinutes: 20,
        taskType: TaskType.quick,
        createdAt: date1,
        scheduledDate: date1,
        timesMoved: 2,
      );

      await db.insertTask(task);
      await db.moveTask('task-move', date2);

      final afterFirstMove = await db.getTasksForDate(date2);
      expect(afterFirstMove.first.timesMoved, 3);

      await db.moveTask('task-move', date3);
      final afterSecondMove = await db.getTasksForDate(date3);
      expect(afterSecondMove.first.timesMoved, 4);
    });

    test('getDroppedTasks returns tasks with status dropped', () async {
      final date = DateTime(2026, 3, 26);

      await db.insertTask(Task(
        id: 'dropped-1',
        title: 'Dropped task',
        pillar: Pillar.work,
        estimatedMinutes: 30,
        taskType: TaskType.quick,
        createdAt: date,
        scheduledDate: date,
      ));
      await db.insertTask(Task(
        id: 'active-1',
        title: 'Active task',
        pillar: Pillar.work,
        estimatedMinutes: 30,
        taskType: TaskType.quick,
        createdAt: date,
        scheduledDate: date,
      ));

      await db.updateTaskStatus('dropped-1', TaskStatus.dropped);

      final dropped = await db.getDroppedTasks();
      expect(dropped.length, 1);
      expect(dropped.first.id, 'dropped-1');
      expect(dropped.first.status, TaskStatus.dropped);
    });
  });

  // ── Beliefs ────────────────────────────────────────────────────────────────

  group('Beliefs', () {
    test('save and retrieve all beliefs', () async {
      final belief1 = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 9.5,
        confidence: 0.7,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 5,
      );
      final belief2 = Belief(
        parameter: BeliefParameter.deepWorkTolerance,
        value: 3.0,
        confidence: 0.5,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 3,
      );

      await db.saveBelief(belief1);
      await db.saveBelief(belief2);

      final beliefs = await db.getAllBeliefs();
      expect(beliefs.length, 2);

      final energy = beliefs.firstWhere(
          (b) => b.parameter == BeliefParameter.peakEnergy);
      expect(energy.value, 9.5);
      expect(energy.confidence, 0.7);
      expect(energy.evidenceCount, 5);
    });

    test('saveBelief upserts (overwrites existing parameter)', () async {
      final original = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 9.0,
        confidence: 0.5,
        lastUpdated: DateTime(2026, 3, 25),
        evidenceCount: 2,
      );
      await db.saveBelief(original);

      final updated = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 10.0,
        confidence: 0.8,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 5,
      );
      await db.saveBelief(updated);

      final beliefs = await db.getAllBeliefs();
      expect(beliefs.length, 1);
      expect(beliefs.first.value, 10.0);
      expect(beliefs.first.confidence, 0.8);
      expect(beliefs.first.evidenceCount, 5);
    });
  });

  // ── WeekConfig ─────────────────────────────────────────────────────────────

  group('WeekConfig', () {
    test('save and get latest week config', () async {
      final config = WeekConfig(
        id: 'week-1',
        weekStartDate: DateTime(2026, 3, 23),
        teachingDays: [1, 3, 5],
        wakeTime: '06:30',
        sleepTime: '22:30',
      );

      await db.saveWeekConfig(config);
      final retrieved = await db.getLatestWeekConfig();

      expect(retrieved, isNotNull);
      expect(retrieved!.id, 'week-1');
      expect(retrieved.teachingDays, [1, 3, 5]);
      expect(retrieved.wakeTime, '06:30');
      expect(retrieved.sleepTime, '22:30');
    });

    test('getLatestWeekConfig returns null when empty', () async {
      final result = await db.getLatestWeekConfig();
      expect(result, isNull);
    });

    test('getLatestWeekConfig returns most recent by week_start_date', () async {
      await db.saveWeekConfig(WeekConfig(
        id: 'week-old',
        weekStartDate: DateTime(2026, 3, 16),
        teachingDays: [2, 4],
      ));
      await db.saveWeekConfig(WeekConfig(
        id: 'week-new',
        weekStartDate: DateTime(2026, 3, 23),
        teachingDays: [1, 3, 5],
      ));

      final latest = await db.getLatestWeekConfig();
      expect(latest!.id, 'week-new');
    });

    test('saveWeekConfig upserts on same id', () async {
      await db.saveWeekConfig(WeekConfig(
        id: 'week-1',
        weekStartDate: DateTime(2026, 3, 23),
        teachingDays: [1, 3],
      ));
      await db.saveWeekConfig(WeekConfig(
        id: 'week-1',
        weekStartDate: DateTime(2026, 3, 23),
        teachingDays: [2, 4, 6],
      ));

      final latest = await db.getLatestWeekConfig();
      expect(latest!.teachingDays, [2, 4, 6]);
    });
  });
}
