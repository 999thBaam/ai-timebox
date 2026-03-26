import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/services/health_tracker.dart';

void main() {
  group('HealthTracker', () {
    group('currentPhase', () {
      test('silent for first 3 days (appDayCount = 1)', () {
        final tracker = HealthTracker(appDayCount: 1);
        expect(tracker.currentPhase, HealthPhase.silent);
      });

      test('silent for appDayCount = 2', () {
        final tracker = HealthTracker(appDayCount: 2);
        expect(tracker.currentPhase, HealthPhase.silent);
      });

      test('silent for appDayCount = 3', () {
        final tracker = HealthTracker(appDayCount: 3);
        expect(tracker.currentPhase, HealthPhase.silent);
      });

      test('gentleNudge for appDayCount = 4', () {
        final tracker = HealthTracker(appDayCount: 4);
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });

      test('gentleNudge for appDayCount = 7', () {
        final tracker = HealthTracker(appDayCount: 7);
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });

      test('patternForming for days 8-21 when acceptedNudgesThisWeek >= 2', () {
        final tracker = HealthTracker(
          appDayCount: 14,
          acceptedNudgesThisWeek: 2,
        );
        expect(tracker.currentPhase, HealthPhase.patternForming);
      });

      test('patternForming for appDayCount = 21 with enough nudges accepted', () {
        final tracker = HealthTracker(
          appDayCount: 21,
          acceptedNudgesThisWeek: 3,
        );
        expect(tracker.currentPhase, HealthPhase.patternForming);
      });

      test('gentleNudge for days 8-21 when acceptedNudgesThisWeek < 2', () {
        final tracker = HealthTracker(
          appDayCount: 14,
          acceptedNudgesThisWeek: 1,
        );
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });

      test('gentleNudge for days 8-21 with 0 accepted nudges', () {
        final tracker = HealthTracker(
          appDayCount: 10,
          acceptedNudgesThisWeek: 0,
        );
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });

      test('habitBuilding for days 22-60', () {
        final tracker = HealthTracker(appDayCount: 30);
        expect(tracker.currentPhase, HealthPhase.habitBuilding);
      });

      test('habitBuilding for appDayCount = 60', () {
        final tracker = HealthTracker(appDayCount: 60);
        expect(tracker.currentPhase, HealthPhase.habitBuilding);
      });

      test('adapted for appDayCount > 60', () {
        final tracker = HealthTracker(appDayCount: 61);
        expect(tracker.currentPhase, HealthPhase.adapted);
      });

      test('adapted for appDayCount = 100', () {
        final tracker = HealthTracker(appDayCount: 100);
        expect(tracker.currentPhase, HealthPhase.adapted);
      });

      test('gentleNudge when skippedFullWeek is true (overrides other logic)', () {
        // Even if we'd normally be in patternForming or adapted,
        // skippedFullWeek forces gentleNudge
        final tracker = HealthTracker(
          appDayCount: 50,
          acceptedNudgesThisWeek: 5,
          skippedFullWeek: true,
        );
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });

      test('dials back to gentleNudge after full week skip regardless of day count', () {
        final tracker = HealthTracker(
          appDayCount: 100,
          skippedFullWeek: true,
        );
        expect(tracker.currentPhase, HealthPhase.gentleNudge);
      });
    });

    group('shouldSuggest', () {
      test('false during silent phase', () {
        final tracker = HealthTracker(appDayCount: 1);
        expect(tracker.shouldSuggest, isFalse);
      });

      test('true during gentleNudge phase', () {
        final tracker = HealthTracker(appDayCount: 5);
        expect(tracker.shouldSuggest, isTrue);
      });

      test('true during patternForming phase', () {
        final tracker = HealthTracker(
          appDayCount: 15,
          acceptedNudgesThisWeek: 3,
        );
        expect(tracker.shouldSuggest, isTrue);
      });

      test('true during habitBuilding phase', () {
        final tracker = HealthTracker(appDayCount: 40);
        expect(tracker.shouldSuggest, isTrue);
      });

      test('true during adapted phase', () {
        final tracker = HealthTracker(appDayCount: 90);
        expect(tracker.shouldSuggest, isTrue);
      });
    });

    group('HealthPhase enum', () {
      test('has all 5 phases', () {
        expect(HealthPhase.values.length, 5);
        expect(HealthPhase.values, contains(HealthPhase.silent));
        expect(HealthPhase.values, contains(HealthPhase.gentleNudge));
        expect(HealthPhase.values, contains(HealthPhase.patternForming));
        expect(HealthPhase.values, contains(HealthPhase.habitBuilding));
        expect(HealthPhase.values, contains(HealthPhase.adapted));
      });
    });
  });
}
