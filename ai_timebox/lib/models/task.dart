import 'enums.dart';

class Task {
  final String id;
  final String title;
  final Pillar pillar;
  final int estimatedMinutes;
  final TaskType taskType;
  final TaskStatus status;
  final DateTime createdAt;
  final DateTime scheduledDate;
  final String? scheduledTime; // "HH:mm"
  final int timesMoved;

  const Task({
    required this.id,
    required this.title,
    required this.pillar,
    required this.estimatedMinutes,
    required this.taskType,
    this.status = TaskStatus.pending,
    required this.createdAt,
    required this.scheduledDate,
    this.scheduledTime,
    this.timesMoved = 0,
  });

  Task copyWith({
    String? id,
    String? title,
    Pillar? pillar,
    int? estimatedMinutes,
    TaskType? taskType,
    TaskStatus? status,
    DateTime? createdAt,
    DateTime? scheduledDate,
    String? scheduledTime,
    int? timesMoved,
  }) {
    return Task(
      id: id ?? this.id,
      title: title ?? this.title,
      pillar: pillar ?? this.pillar,
      estimatedMinutes: estimatedMinutes ?? this.estimatedMinutes,
      taskType: taskType ?? this.taskType,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      scheduledDate: scheduledDate ?? this.scheduledDate,
      scheduledTime: scheduledTime ?? this.scheduledTime,
      timesMoved: timesMoved ?? this.timesMoved,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'pillar': pillar.name,
      'estimated_minutes': estimatedMinutes,
      'task_type': taskType.name,
      'status': status.name,
      'created_at': createdAt.millisecondsSinceEpoch,
      'scheduled_date': scheduledDate.millisecondsSinceEpoch,
      'scheduled_time': scheduledTime,
      'times_moved': timesMoved,
    };
  }

  factory Task.fromMap(Map<String, dynamic> map) {
    return Task(
      id: map['id'] as String,
      title: map['title'] as String,
      pillar: Pillar.values.byName(map['pillar'] as String),
      estimatedMinutes: map['estimated_minutes'] as int,
      taskType: TaskType.values.byName(map['task_type'] as String),
      status: TaskStatus.values.byName(map['status'] as String),
      createdAt: DateTime.fromMillisecondsSinceEpoch(map['created_at'] as int),
      scheduledDate:
          DateTime.fromMillisecondsSinceEpoch(map['scheduled_date'] as int),
      scheduledTime: map['scheduled_time'] as String?,
      timesMoved: map['times_moved'] as int,
    );
  }
}
