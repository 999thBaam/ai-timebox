import 'package:flutter/material.dart';
import '../models/enums.dart';

class DayPill extends StatelessWidget {
  final String label;
  final int dayNumber;
  final DayType dayType;
  final bool isToday;
  final int taskCount;
  final VoidCallback onTap;

  const DayPill({
    super.key,
    required this.label,
    required this.dayNumber,
    required this.dayType,
    required this.isToday,
    required this.taskCount,
    required this.onTap,
  });

  _DayPillStyle _getStyle() {
    if (isToday) {
      return const _DayPillStyle(
        bg: Color(0x14FFFFFF),
        textColor: Colors.white,
        borderColor: Color(0x26FFFFFF),
        hasBorder: true,
      );
    }
    switch (dayType) {
      case DayType.teaching:
        return const _DayPillStyle(
          bg: Color(0x1F6366F1),
          textColor: Color(0xFF818CF8),
          borderColor: Colors.transparent,
          hasBorder: false,
        );
      case DayType.free:
        return const _DayPillStyle(
          bg: Color(0x08FFFFFF),
          textColor: Color(0xFF64748B),
          borderColor: Colors.transparent,
          hasBorder: false,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final style = _getStyle();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 32,
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: style.bg,
          borderRadius: BorderRadius.circular(10),
          border: style.hasBorder
              ? Border.all(color: style.borderColor, width: 1.5)
              : null,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: style.textColor,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '$dayNumber',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: style.textColor,
              ),
            ),
            if (taskCount > 0) ...[
              const SizedBox(height: 3),
              Container(
                width: 4,
                height: 4,
                decoration: BoxDecoration(
                  color: style.textColor.withValues(alpha: 0.5),
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DayPillStyle {
  final Color bg;
  final Color textColor;
  final Color borderColor;
  final bool hasBorder;

  const _DayPillStyle({
    required this.bg,
    required this.textColor,
    required this.borderColor,
    required this.hasBorder,
  });
}
