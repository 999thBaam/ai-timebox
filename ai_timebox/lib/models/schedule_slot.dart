import 'enums.dart';

class ScheduleSlot {
  final String? taskId;
  final SlotType slotType;
  final String startTime;
  final String endTime;
  final String title;
  final Pillar? pillar;

  const ScheduleSlot({
    this.taskId,
    required this.slotType,
    required this.startTime,
    required this.endTime,
    required this.title,
    this.pillar,
  });

  factory ScheduleSlot.fromJson(Map<String, dynamic> json) {
    return ScheduleSlot(
      taskId: json['task_id'] as String?,
      slotType: _parseSlotType(json['slot_type'] as String),
      startTime: json['start_time'] as String,
      endTime: json['end_time'] as String,
      title: json['title'] as String,
      pillar: json['pillar'] != null
          ? Pillar.values.byName(json['pillar'] as String)
          : null,
    );
  }

  static SlotType _parseSlotType(String raw) {
    switch (raw) {
      case 'health_nudge':
        return SlotType.healthNudge;
      default:
        return SlotType.values.byName(raw);
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'task_id': taskId,
      'slot_type': _slotTypeToString(slotType),
      'start_time': startTime,
      'end_time': endTime,
      'title': title,
      'pillar': pillar?.name,
    };
  }

  static String _slotTypeToString(SlotType type) {
    switch (type) {
      case SlotType.healthNudge:
        return 'health_nudge';
      default:
        return type.name;
    }
  }
}
