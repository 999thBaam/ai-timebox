import 'package:flutter/cupertino.dart';
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
  final FocusNode _focusNode = FocusNode();
  bool _hasText = false;

  void _handleSubmit(String value) {
    final trimmed = value.trim();
    if (trimmed.isNotEmpty) {
      widget.onSubmit(trimmed);
      _controller.clear();
      setState(() => _hasText = false);
      // Keep keyboard open for rapid task entry
      _focusNode.requestFocus();
    }
  }

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      final has = _controller.text.trim().isNotEmpty;
      if (has != _hasText) setState(() => _hasText = has);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: CupertinoTextField(
            controller: _controller,
            focusNode: _focusNode,
            onSubmitted: _handleSubmit,
            textInputAction: TextInputAction.done,
            keyboardAppearance: Brightness.dark,
            autocorrect: true,
            enableSuggestions: true,
            placeholder: 'Add a task...',
            placeholderStyle: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 15,
            ),
            style: const TextStyle(
              color: Color(0xFFF1F5F9),
              fontSize: 15,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0x0DFFFFFF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0x14FFFFFF)),
            ),
            cursorColor: const Color(0xFF818CF8),
            suffix: _hasText
                ? GestureDetector(
                    onTap: () => _handleSubmit(_controller.text),
                    child: const Padding(
                      padding: EdgeInsets.only(right: 10),
                      child: Icon(
                        CupertinoIcons.arrow_up_circle_fill,
                        color: Color(0xFF818CF8),
                        size: 24,
                      ),
                    ),
                  )
                : null,
          ),
        ),
        if (widget.showMic) ...[
          const SizedBox(width: 8),
          GestureDetector(
            onTap: widget.onMicTap,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0x266366F1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                CupertinoIcons.mic,
                color: Color(0xFF818CF8),
                size: 20,
              ),
            ),
          ),
        ],
      ],
    );
  }
}
