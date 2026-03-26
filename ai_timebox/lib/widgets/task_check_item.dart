import 'package:flutter/material.dart';

class TaskCheckItem extends StatelessWidget {
  final String title;
  final bool isDone;
  final VoidCallback onTap;
  final Widget? trailingWidget;

  const TaskCheckItem({
    super.key,
    required this.title,
    required this.isDone,
    required this.onTap,
    this.trailingWidget,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: const BoxDecoration(
          border: Border(
            bottom: BorderSide(color: Color(0x0AFFFFFF)),
          ),
        ),
        child: Row(
          children: [
            // Circle checkbox
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isDone
                    ? const Color(0x2634D399) // rgba(52,211,153,0.15)
                    : Colors.transparent,
                border: Border.all(
                  color: isDone
                      ? const Color(0xFF34D399)
                      : const Color(0x2AFFFFFF), // rgba(255,255,255,0.15) ≈ 0x26
                  width: 1.5,
                ),
              ),
              child: isDone
                  ? const Icon(
                      Icons.check,
                      size: 13,
                      color: Color(0xFF34D399),
                    )
                  : null,
            ),
            const SizedBox(width: 10),
            // Title
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: 13.5,
                  color: isDone
                      ? const Color(0xFF64748B)
                      : const Color(0xFFE2E8F0),
                  decoration: isDone ? TextDecoration.lineThrough : null,
                  decorationColor:
                      isDone ? const Color(0xFF64748B) : null,
                ),
              ),
            ),
            if (trailingWidget != null) ...[
              const SizedBox(width: 8),
              trailingWidget!,
            ],
          ],
        ),
      ),
    );
  }
}
