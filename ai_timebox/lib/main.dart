import 'package:flutter/material.dart';
import 'storage/local_db.dart';
import 'screens/setup_screen.dart';
import 'screens/daily_screen.dart';
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
      home: const _AppRouter(),
    );
  }
}

/// Checks for an existing WeekConfig and routes to the correct first screen.
class _AppRouter extends StatefulWidget {
  const _AppRouter();

  @override
  State<_AppRouter> createState() => _AppRouterState();
}

class _AppRouterState extends State<_AppRouter> {
  late final Future<bool> _hasConfigFuture;

  @override
  void initState() {
    super.initState();
    _hasConfigFuture = _checkWeekConfig();
  }

  Future<bool> _checkWeekConfig() async {
    final db = LocalDb();
    await db.init();
    final config = await db.getLatestWeekConfig();
    await db.close();
    return config != null;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _hasConfigFuture,
      builder: (context, snapshot) {
        // Show a blank dark screen while loading
        if (!snapshot.hasData) {
          return const Scaffold(
            backgroundColor: AppColors.background,
            body: SizedBox.shrink(),
          );
        }

        final hasConfig = snapshot.data!;

        if (!hasConfig) {
          return const SetupScreen();
        }

        return const DailyScreen();
      },
    );
  }
}
