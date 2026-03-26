import 'package:flutter/material.dart';

class TaskInput extends StatefulWidget {
  final void Function(String) onSubmit;
  final VoidCallback onMicTap;
  final bool showMic;

  const TaskInput({
    super.key,
    required this.onSubmit,
    required this.onMicTap,
    this.showMic = true,
  });

  @override
  State<TaskInput> createState() => _TaskInputState();
}

class _TaskInputState extends State<TaskInput> {
  final TextEditingController _controller = TextEditingController();

  void _handleSubmit(String value) {
    final trimmed = value.trim();
    if (trimmed.isNotEmpty) {
      widget.onSubmit(trimmed);
      _controller.clear();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _controller,
            onSubmitted: _handleSubmit,
            style: const TextStyle(
              color: Color(0xFFF1F5F9),
              fontSize: 14,
            ),
            decoration: InputDecoration(
              filled: true,
              fillColor: const Color(0x0DFFFFFF),
              hintText: 'Add a task...',
              hintStyle: const TextStyle(color: Color(0xFF64748B)),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 10,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0x14FFFFFF)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0x14FFFFFF)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(
                  color: Color(0xFF818CF8),
                  width: 1.5,
                ),
              ),
            ),
          ),
        ),
        if (widget.showMic) ...[
          const SizedBox(width: 8),
          GestureDetector(
            onTap: widget.onMicTap,
            child: Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: const Color(0x266366F1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.mic,
                color: Color(0xFF818CF8),
                size: 18,
              ),
            ),
          ),
        ],
      ],
    );
  }
}
