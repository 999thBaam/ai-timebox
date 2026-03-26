import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

class NotificationService {
  static const _morningHourKey = 'notif_morning_hour';
  static const _morningMinuteKey = 'notif_morning_minute';
  static const _eveningHourKey = 'notif_evening_hour';
  static const _eveningMinuteKey = 'notif_evening_minute';

  static const int _morningId = 1;
  static const int _eveningId = 2;

  static const TimeOfDay _defaultMorning = TimeOfDay(hour: 8, minute: 0);
  static const TimeOfDay _defaultEvening = TimeOfDay(hour: 21, minute: 0);

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  Future<void> init() async {
    tz_data.initializeTimeZones();

    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(iOS: iosSettings);

    await _plugin.initialize(initSettings);
  }

  // ── Scheduling ──────────────────────────────────────────────────────────

  /// Schedules a daily morning notification at [time].
  /// Saves the chosen time to shared_preferences.
  Future<void> scheduleMorning(TimeOfDay time) async {
    await _saveTime(_morningHourKey, _morningMinuteKey, time);
    await _scheduleDailyAtTime(
      id: _morningId,
      time: time,
      title: 'Good morning',
      body: 'Ready to plan your day?',
    );
  }

  /// Schedules a daily evening notification at [time].
  /// Saves the chosen time to shared_preferences.
  Future<void> scheduleEvening(TimeOfDay time) async {
    await _saveTime(_eveningHourKey, _eveningMinuteKey, time);
    await _scheduleDailyAtTime(
      id: _eveningId,
      time: time,
      title: 'Evening check-in',
      body: 'How did today go?',
    );
  }

  /// Cancels all scheduled notifications.
  Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }

  // ── Stored times ────────────────────────────────────────────────────────

  Future<TimeOfDay> getMorningTime() async {
    final prefs = await SharedPreferences.getInstance();
    final hour = prefs.getInt(_morningHourKey) ?? _defaultMorning.hour;
    final minute = prefs.getInt(_morningMinuteKey) ?? _defaultMorning.minute;
    return TimeOfDay(hour: hour, minute: minute);
  }

  Future<TimeOfDay> getEveningTime() async {
    final prefs = await SharedPreferences.getInstance();
    final hour = prefs.getInt(_eveningHourKey) ?? _defaultEvening.hour;
    final minute = prefs.getInt(_eveningMinuteKey) ?? _defaultEvening.minute;
    return TimeOfDay(hour: hour, minute: minute);
  }

  /// Schedules both morning and evening at their default times.
  /// Called on first launch.
  Future<void> scheduleDefaults() async {
    await scheduleMorning(_defaultMorning);
    await scheduleEvening(_defaultEvening);
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  Future<void> _saveTime(
    String hourKey,
    String minuteKey,
    TimeOfDay time,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(hourKey, time.hour);
    await prefs.setInt(minuteKey, time.minute);
  }

  Future<void> _scheduleDailyAtTime({
    required int id,
    required TimeOfDay time,
    required String title,
    required String body,
  }) async {
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(iOS: iosDetails);

    // Cancel existing notification with this id before rescheduling
    await _plugin.cancel(id);

    final now = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(
      tz.local,
      now.year,
      now.month,
      now.day,
      time.hour,
      time.minute,
    );

    // If the time has already passed today, schedule for tomorrow
    if (scheduled.isBefore(now)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }

    await _plugin.zonedSchedule(
      id,
      title,
      body,
      scheduled,
      details,
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      matchDateTimeComponents: DateTimeComponents.time,
    );
  }
}
