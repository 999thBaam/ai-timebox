import 'package:flutter/material.dart';
import 'theme.dart';

void main() {
  runApp(const AiTimeboxApp());
}

class AiTimeboxApp extends StatelessWidget {
  const AiTimeboxApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Timebox',
      theme: appTheme,
      debugShowCheckedModeBanner: false,
      home: const _PlaceholderHome(),
    );
  }
}

class _PlaceholderHome extends StatelessWidget {
  const _PlaceholderHome();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI Timebox')),
      body: const Center(
        child: Text(
          'AI Timebox',
          style: TextStyle(
            fontSize: 32,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
