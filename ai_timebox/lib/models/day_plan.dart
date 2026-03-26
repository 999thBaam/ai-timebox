import 'enums.dart';

class DayPlan {
  final String id;
  final DateTime date;
  final DayType dayType;
  final String wakeTime;
  final String sleepTime;
  final String scheduleJson;
  final String? insight;

  const DayPlan({
    required this.id,
    required this.date,
    required this.dayType,
    required this.wakeTime,
    required this.sleepTime,
    this.scheduleJson = '[]',
    this.insight,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'date': date.millisecondsSinceEpoch,
      'day_type': dayType.name,
      'wake_time': wakeTime,
      'sleep_time': sleepTime,
      'schedule_json': scheduleJson,
      'insight': insight,
    };
  }

  factory DayPlan.fromMap(Map<String, dynamic> map) {
    return DayPlan(
      id: map['id'] as String,
      date: DateTime.fromMillisecondsSinceEpoch(map['date'] as int),
      dayType: DayType.values.byName(map['day_type'] as String),
      wakeTime: map['wake_time'] as String,
      sleepTime: map['sleep_time'] as String,
      scheduleJson: map['schedule_json'] as String? ?? '[]',
      insight: map['insight'] as String?,
    );
  }
}
