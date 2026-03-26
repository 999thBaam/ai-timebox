import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'services/notification_service.dart';
import 'storage/local_db.dart';
import 'screens/setup_screen.dart';
import 'screens/daily_screen.dart';
import 'theme.dart';

/// Global DB instance — opened once, stays open for app lifetime.
final db = LocalDb();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AiTimeboxApp());
}

/// Runs notification setup in background after first frame renders.
Future<void> _initNotifications() async {
  try {
    final notificationService = NotificationService();
    await notificationService.init();

    final prefs = await SharedPreferences.getInstance();
    final notificationsScheduled =
        prefs.getBool('notifications_scheduled') ?? false;
    if (!notificationsScheduled) {
      await notificationService.scheduleDefaults();
      await prefs.setBool('notifications_scheduled', true);
    }
  } catch (e) {
    debugPrint('Notification init failed: $e');
  }
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
    _initNotifications();
  }

  Future<bool> _checkWeekConfig() async {
    await db.init();
    final config = await db.getLatestWeekConfig();
    return config != null;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _hasConfigFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(
            backgroundColor: AppColors.background,
            body: SizedBox.shrink(),
          );
        }

        if (!snapshot.data!) {
          return const SetupScreen();
        }

        return const DailyScreen();
      },
    );
  }
}
