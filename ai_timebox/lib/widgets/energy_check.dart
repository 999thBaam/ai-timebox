import 'dart:async';
import 'package:flutter/material.dart';

class EnergyCheck extends StatefulWidget {
  final void Function(String level) onReport;
  final VoidCallback onDismiss;

  const EnergyCheck({
    super.key,
    required this.onReport,
    required this.onDismiss,
  });

  @override
  State<EnergyCheck> createState() => _EnergyCheckState();
}

class _EnergyCheckState extends State<EnergyCheck>
    with SingleTickerProviderStateMixin {
  late final AnimationController _animController;
  late final Animation<double> _fadeAnim;
  Timer? _dismissTimer;

  @override
  void initState() {
    super.initState();

    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnim = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
      reverseCurve: Curves.easeIn,
    );

    _animController.forward();

    _dismissTimer = Timer(const Duration(seconds: 10), _autoDismiss);
  }

  void _autoDismiss() {
    _animController.reverse().then((_) {
      if (mounted) widget.onDismiss();
    });
  }

  void _handleReport(String level) {
    _dismissTimer?.cancel();
    _animController.reverse().then((_) {
      if (mounted) widget.onReport(level);
    });
  }

  void _handleDismiss() {
    _dismissTimer?.cancel();
    _autoDismiss();
  }

  @override
  void dispose() {
    _dismissTimer?.cancel();
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnim,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0x14FFFFFF),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0x0FFFFFFF)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'How was that? 🔋',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: Color(0xFFF1F5F9),
              ),
            ),
            const SizedBox(width: 12),
            _EnergyButton(
              label: 'Low',
              onTap: () => _handleReport('low'),
              foregroundColor: const Color(0xFF64748B),
              backgroundColor: const Color(0x0AFFFFFF),
            ),
            const SizedBox(width: 6),
            _EnergyButton(
              label: 'OK',
              onTap: () => _handleReport('ok'),
              foregroundColor: const Color(0xFF94A3B8),
              backgroundColor: const Color(0x14FFFFFF),
            ),
            const SizedBox(width: 6),
            _EnergyButton(
              label: 'Great',
              onTap: () => _handleReport('great'),
              foregroundColor: const Color(0xFF34D399),
              backgroundColor: const Color(0x1A34D399),
            ),
            const SizedBox(width: 6),
            GestureDetector(
              onTap: _handleDismiss,
              child: const Icon(
                Icons.close,
                size: 14,
                color: Color(0xFF475569),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EnergyButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final Color foregroundColor;
  final Color backgroundColor;

  const _EnergyButton({
    required this.label,
    required this.onTap,
    required this.foregroundColor,
    required this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: foregroundColor,
          ),
        ),
      ),
    );
  }
}
