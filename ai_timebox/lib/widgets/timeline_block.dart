import 'package:flutter/material.dart';
import '../models/enums.dart';
import '../theme.dart';

class TimelineBlock extends StatelessWidget {
  final String startTime;
  final String endTime;
  final String title;
  final Pillar? pillar;
  final SlotType slotType;
  final VoidCallback onTap;

  const TimelineBlock({
    super.key,
    required this.startTime,
    required this.endTime,
    required this.title,
    this.pillar,
    required this.slotType,
    required this.onTap,
  });

  _PillarStyle _getStyle() {
    switch (pillar) {
      case Pillar.work:
        return _PillarStyle(
          bg: AppColors.workBg,
          borderColor: const Color(0xFF818CF8),
          subtitleColor: const Color(0xFFA5B4FC),
        );
      case Pillar.health:
        return _PillarStyle(
          bg: AppColors.healthBg,
          borderColor: AppColors.healthPrimary,
          subtitleColor: const Color(0xFF6EE7B7),
        );
      case Pillar.errand:
        return _PillarStyle(
          bg: AppColors.errandBg,
          borderColor: AppColors.errandPrimary,
          subtitleColor: const Color(0xFFFBBF24),
        );
      case Pillar.social:
        return _PillarStyle(
          bg: AppColors.socialBg,
          borderColor: AppColors.socialPrimary,
          subtitleColor: const Color(0xFFFDA4AF),
        );
      case null:
        return _PillarStyle(
          bg: const Color(0x08FFFFFF),
          borderColor: Colors.transparent,
          subtitleColor: AppColors.textMuted,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final style = _getStyle();
    final isOpen = pillar == null;

    return Opacity(
      opacity: isOpen ? 0.5 : 1.0,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Time column
            SizedBox(
              width: 42,
              child: Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Text(
                  startTime,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFF64748B),
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            // Card
            Expanded(
              child: Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  color: style.bg,
                  borderRadius: BorderRadius.circular(14),
                  border: isOpen
                      ? null
                      : Border(
                          left: BorderSide(
                            color: style.borderColor,
                            width: 3,
                          ),
                        ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFF1F5F9),
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '$startTime – $endTime',
                      style: TextStyle(
                        fontSize: 11,
                        color: style.subtitleColor,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PillarStyle {
  final Color bg;
  final Color borderColor;
  final Color subtitleColor;

  const _PillarStyle({
    required this.bg,
    required this.borderColor,
    required this.subtitleColor,
  });
}
