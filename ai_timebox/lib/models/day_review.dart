class DayReview {
  final String id;
  final DateTime date;
  final int completedCount;
  final int totalCount;
  final int streakDay;

  const DayReview({
    required this.id,
    required this.date,
    required this.completedCount,
    required this.totalCount,
    required this.streakDay,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'date': date.millisecondsSinceEpoch,
      'completed_count': completedCount,
      'total_count': totalCount,
      'streak_day': streakDay,
    };
  }

  factory DayReview.fromMap(Map<String, dynamic> map) {
    return DayReview(
      id: map['id'] as String,
      date: DateTime.fromMillisecondsSinceEpoch(map['date'] as int),
      completedCount: map['completed_count'] as int,
      totalCount: map['total_count'] as int,
      streakDay: map['streak_day'] as int,
    );
  }
}
