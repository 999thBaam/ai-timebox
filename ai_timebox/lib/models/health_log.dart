class HealthLog {
  final String id;
  final DateTime date;
  final String activityType;
  final int durationMinutes;
  final bool wasSuggested;

  const HealthLog({
    required this.id,
    required this.date,
    required this.activityType,
    required this.durationMinutes,
    required this.wasSuggested,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'date': date.millisecondsSinceEpoch,
      'activity_type': activityType,
      'duration_minutes': durationMinutes,
      'was_suggested': wasSuggested ? 1 : 0,
    };
  }

  factory HealthLog.fromMap(Map<String, dynamic> map) {
    return HealthLog(
      id: map['id'] as String,
      date: DateTime.fromMillisecondsSinceEpoch(map['date'] as int),
      activityType: map['activity_type'] as String,
      durationMinutes: map['duration_minutes'] as int,
      wasSuggested: (map['was_suggested'] as int) == 1,
    );
  }
}
