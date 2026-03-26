import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart' as path;
import '../models/task.dart';
import '../models/belief.dart';
import '../models/week_config.dart';
import '../models/day_plan.dart';
import '../models/health_log.dart';
import '../models/day_review.dart';
import '../models/enums.dart';

class LocalDb {
  Database? _db;

  // ── Init / Close ──────────────────────────────────────────────────────────

  Future<void> init({bool inMemory = false}) async {
    final factory = inMemory ? databaseFactoryFfi : databaseFactory;

    final dbPath = inMemory
        ? inMemoryDatabasePath
        : path.join(await getDatabasesPath(), 'ai_timebox.db');

    _db = await factory.openDatabase(
      dbPath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: _onCreate,
      ),
    );
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }

  Database get _database {
    final db = _db;
    if (db == null) throw StateError('LocalDb not initialised — call init()');
    return db;
  }

  // ── Schema ────────────────────────────────────────────────────────────────

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        pillar TEXT NOT NULL,
        estimated_minutes INTEGER NOT NULL,
        task_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at INTEGER NOT NULL,
        scheduled_date INTEGER NOT NULL,
        scheduled_time TEXT,
        times_moved INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE beliefs (
        parameter TEXT PRIMARY KEY,
        value REAL NOT NULL,
        confidence REAL NOT NULL,
        last_updated INTEGER NOT NULL,
        evidence_count INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE week_configs (
        id TEXT PRIMARY KEY,
        week_start_date INTEGER NOT NULL,
        teaching_days TEXT NOT NULL,
        wake_time TEXT NOT NULL DEFAULT '07:00',
        sleep_time TEXT NOT NULL DEFAULT '23:00'
      )
    ''');

    await db.execute('''
      CREATE TABLE day_plans (
        id TEXT PRIMARY KEY,
        date INTEGER NOT NULL UNIQUE,
        day_type TEXT NOT NULL,
        wake_time TEXT NOT NULL,
        sleep_time TEXT NOT NULL,
        schedule_json TEXT NOT NULL DEFAULT '[]',
        insight TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE health_logs (
        id TEXT PRIMARY KEY,
        date INTEGER NOT NULL,
        activity_type TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        was_suggested INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE day_reviews (
        id TEXT PRIMARY KEY,
        date INTEGER NOT NULL UNIQUE,
        completed_count INTEGER NOT NULL,
        total_count INTEGER NOT NULL,
        streak_day INTEGER NOT NULL DEFAULT 0
      )
    ''');
  }

  // ── Tasks ─────────────────────────────────────────────────────────────────

  Future<void> insertTask(Task task) async {
    await _database.insert(
      'tasks',
      task.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Returns all tasks whose scheduled_date falls on [date] (ignoring time).
  Future<List<Task>> getTasksForDate(DateTime date) async {
    final dayStart = DateTime(date.year, date.month, date.day);
    final dayEnd = dayStart.add(const Duration(days: 1));

    final rows = await _database.query(
      'tasks',
      where: 'scheduled_date >= ? AND scheduled_date < ?',
      whereArgs: [
        dayStart.millisecondsSinceEpoch,
        dayEnd.millisecondsSinceEpoch,
      ],
    );

    return rows.map(Task.fromMap).toList();
  }

  Future<void> updateTaskStatus(String id, TaskStatus status) async {
    await _database.update(
      'tasks',
      {'status': status.name},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  /// Moves a task to [newDate]: sets scheduled_date, status=moved, increments
  /// times_moved by 1.
  Future<void> moveTask(String id, DateTime newDate) async {
    final rows = await _database.query(
      'tasks',
      columns: ['times_moved'],
      where: 'id = ?',
      whereArgs: [id],
    );

    if (rows.isEmpty) return;

    final currentTimesMoved = rows.first['times_moved'] as int;
    final newDay = DateTime(newDate.year, newDate.month, newDate.day);

    await _database.update(
      'tasks',
      {
        'scheduled_date': newDay.millisecondsSinceEpoch,
        'status': TaskStatus.moved.name,
        'times_moved': currentTimesMoved + 1,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<List<Task>> getDroppedTasks() async {
    final rows = await _database.query(
      'tasks',
      where: 'status = ?',
      whereArgs: [TaskStatus.dropped.name],
    );
    return rows.map(Task.fromMap).toList();
  }

  // ── Beliefs ───────────────────────────────────────────────────────────────

  /// Upserts a belief (insert or replace on parameter PK).
  Future<void> saveBelief(Belief belief) async {
    await _database.insert(
      'beliefs',
      belief.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Belief>> getAllBeliefs() async {
    final rows = await _database.query('beliefs');
    return rows.map(Belief.fromMap).toList();
  }

  // ── WeekConfig ────────────────────────────────────────────────────────────

  /// Upserts a week config (insert or replace on id PK).
  Future<void> saveWeekConfig(WeekConfig config) async {
    await _database.insert(
      'week_configs',
      config.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Returns the WeekConfig with the most recent week_start_date, or null.
  Future<WeekConfig?> getLatestWeekConfig() async {
    final rows = await _database.query(
      'week_configs',
      orderBy: 'week_start_date DESC',
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return WeekConfig.fromMap(rows.first);
  }

  // ── DayPlan ───────────────────────────────────────────────────────────────

  /// Upserts a day plan.
  Future<void> saveDayPlan(DayPlan plan) async {
    await _database.insert(
      'day_plans',
      plan.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Returns the DayPlan for [date] (date-only match), or null.
  Future<DayPlan?> getDayPlan(DateTime date) async {
    final dayStart = DateTime(date.year, date.month, date.day);
    final dayEnd = dayStart.add(const Duration(days: 1));

    final rows = await _database.query(
      'day_plans',
      where: 'date >= ? AND date < ?',
      whereArgs: [
        dayStart.millisecondsSinceEpoch,
        dayEnd.millisecondsSinceEpoch,
      ],
      limit: 1,
    );

    if (rows.isEmpty) return null;
    return DayPlan.fromMap(rows.first);
  }

  // ── HealthLog ─────────────────────────────────────────────────────────────

  Future<void> insertHealthLog(HealthLog log) async {
    await _database.insert(
      'health_logs',
      log.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Returns all health logs whose date falls within the 7-day window
  /// starting at [weekStart].
  Future<List<HealthLog>> getHealthLogsForWeek(DateTime weekStart) async {
    final start = DateTime(weekStart.year, weekStart.month, weekStart.day);
    final end = start.add(const Duration(days: 7));

    final rows = await _database.query(
      'health_logs',
      where: 'date >= ? AND date < ?',
      whereArgs: [
        start.millisecondsSinceEpoch,
        end.millisecondsSinceEpoch,
      ],
    );

    return rows.map(HealthLog.fromMap).toList();
  }

  // ── DayReview ─────────────────────────────────────────────────────────────

  /// Upserts a day review.
  Future<void> saveDayReview(DayReview review) async {
    await _database.insert(
      'day_reviews',
      review.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Returns the DayReview for [date] (date-only match), or null.
  Future<DayReview?> getDayReview(DateTime date) async {
    final dayStart = DateTime(date.year, date.month, date.day);
    final dayEnd = dayStart.add(const Duration(days: 1));

    final rows = await _database.query(
      'day_reviews',
      where: 'date >= ? AND date < ?',
      whereArgs: [
        dayStart.millisecondsSinceEpoch,
        dayEnd.millisecondsSinceEpoch,
      ],
      limit: 1,
    );

    if (rows.isEmpty) return null;
    return DayReview.fromMap(rows.first);
  }

  /// Returns the current streak length by counting consecutive days ending
  /// today (or the most recent review day) where streak_day > 0.
  /// Simply returns the maximum streak_day value across all reviews, which
  /// equals the current streak length when reviews are saved correctly.
  Future<int> getCurrentStreak() async {
    final rows = await _database.query(
      'day_reviews',
      columns: ['streak_day'],
      orderBy: 'date DESC',
      limit: 1,
    );
    if (rows.isEmpty) return 0;
    return (rows.first['streak_day'] as int?) ?? 0;
  }
}
