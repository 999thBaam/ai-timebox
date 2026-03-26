class WeekConfig {
  final String id;
  final DateTime weekStartDate;
  final List<int> teachingDays;
  final String wakeTime;
  final String sleepTime;

  const WeekConfig({
    required this.id,
    required this.weekStartDate,
    required this.teachingDays,
    this.wakeTime = '07:00',
    this.sleepTime = '23:00',
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'week_start_date': weekStartDate.millisecondsSinceEpoch,
      'teaching_days': teachingDays.join(','),
      'wake_time': wakeTime,
      'sleep_time': sleepTime,
    };
  }

  factory WeekConfig.fromMap(Map<String, dynamic> map) {
    final raw = map['teaching_days'] as String? ?? '';
    final days = raw.isEmpty
        ? <int>[]
        : raw.split(',').map((s) => int.parse(s.trim())).toList();

    return WeekConfig(
      id: map['id'] as String,
      weekStartDate:
          DateTime.fromMillisecondsSinceEpoch(map['week_start_date'] as int),
      teachingDays: days,
      wakeTime: map['wake_time'] as String? ?? '07:00',
      sleepTime: map['sleep_time'] as String? ?? '23:00',
    );
  }
}
