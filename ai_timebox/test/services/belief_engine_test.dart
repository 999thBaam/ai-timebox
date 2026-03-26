import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/belief.dart';
import 'package:ai_timebox/services/belief_engine.dart';

void main() {
  group('BeliefEngine', () {
    late BeliefEngine engine;
    late Map<BeliefParameter, Belief> beliefs;

    setUp(() {
      engine = BeliefEngine();
      beliefs = engine.getDefaultBeliefs();
    });

    group('getDefaultBeliefs', () {
      test('returns 6 beliefs', () {
        expect(beliefs.length, 6);
      });

      test('all beliefs have confidence 0.3', () {
        for (final belief in beliefs.values) {
          expect(belief.confidence, closeTo(0.3, 0.0001));
        }
      });

      test('peakEnergy default is 10.0', () {
        expect(beliefs[BeliefParameter.peakEnergy]!.value, closeTo(10.0, 0.0001));
      });

      test('deepWorkTolerance default is 60.0', () {
        expect(beliefs[BeliefParameter.deepWorkTolerance]!.value, closeTo(60.0, 0.0001));
      });

      test('contextSwitchCost default is 0.5', () {
        expect(beliefs[BeliefParameter.contextSwitchCost]!.value, closeTo(0.5, 0.0001));
      });

      test('chaosTolerance default is 0.4', () {
        expect(beliefs[BeliefParameter.chaosTolerance]!.value, closeTo(0.4, 0.0001));
      });

      test('meetingTolerance default is 0.5', () {
        expect(beliefs[BeliefParameter.meetingTolerance]!.value, closeTo(0.5, 0.0001));
      });

      test('recoveryRate default is 0.10', () {
        expect(beliefs[BeliefParameter.recoveryRate]!.value, closeTo(0.10, 0.0001));
      });

      test('contains all 6 BeliefParameter keys', () {
        expect(beliefs.containsKey(BeliefParameter.peakEnergy), isTrue);
        expect(beliefs.containsKey(BeliefParameter.deepWorkTolerance), isTrue);
        expect(beliefs.containsKey(BeliefParameter.contextSwitchCost), isTrue);
        expect(beliefs.containsKey(BeliefParameter.chaosTolerance), isTrue);
        expect(beliefs.containsKey(BeliefParameter.meetingTolerance), isTrue);
        expect(beliefs.containsKey(BeliefParameter.recoveryRate), isTrue);
      });
    });

    group('processTaskCompletion', () {
      test('shifts peakEnergy toward taskStartHour', () {
        final original = beliefs[BeliefParameter.peakEnergy]!.value; // 10.0
        final updated = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 14,
          durationMinutes: 60,
        );
        // peakEnergy should shift toward 14
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          greaterThan(original),
        );
      });

      test('shifts deepWorkTolerance toward duration', () {
        // default deepWorkTolerance = 60.0, use duration 90 → should shift up
        final updated = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 10,
          durationMinutes: 90,
        );
        expect(
          updated[BeliefParameter.deepWorkTolerance]!.value,
          greaterThan(60.0),
        );
      });

      test('reduces contextSwitchCost when minutesSinceLastBlock < 15', () {
        final original = beliefs[BeliefParameter.contextSwitchCost]!.value; // 0.5
        final updated = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 10,
          durationMinutes: 60,
          minutesSinceLastBlock: 10,
        );
        expect(
          updated[BeliefParameter.contextSwitchCost]!.value,
          lessThan(original),
        );
      });

      test('does not reduce contextSwitchCost when minutesSinceLastBlock >= 15', () {
        final original = beliefs[BeliefParameter.contextSwitchCost]!.value;
        final updated = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 10,
          durationMinutes: 60,
          minutesSinceLastBlock: 20,
        );
        expect(
          updated[BeliefParameter.contextSwitchCost]!.value,
          closeTo(original, 0.0001),
        );
      });

      test('does not reduce contextSwitchCost when minutesSinceLastBlock is null', () {
        final original = beliefs[BeliefParameter.contextSwitchCost]!.value;
        final updated = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 10,
          durationMinutes: 60,
        );
        expect(
          updated[BeliefParameter.contextSwitchCost]!.value,
          closeTo(original, 0.0001),
        );
      });

      test('returns updated map without mutating original', () {
        final originalPeak = beliefs[BeliefParameter.peakEnergy]!.value;
        engine.processTaskCompletion(
          beliefs,
          taskStartHour: 14,
          durationMinutes: 60,
        );
        // original map unchanged
        expect(beliefs[BeliefParameter.peakEnergy]!.value, closeTo(originalPeak, 0.0001));
      });
    });

    group('processSkip', () {
      test('pushes peakEnergy to opposite hour (hour > 12)', () {
        // skippedHour=14 → opposite = 14-12=2
        // current peak=10.0 → should move toward 2 (decrease)
        final updated = engine.processSkip(beliefs, skippedHour: 14);
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          lessThan(10.0),
        );
      });

      test('pushes peakEnergy to opposite hour (hour <= 12)', () {
        // skippedHour=8 → opposite = 8+12=20
        // current peak=10.0 → should move toward 20 (increase)
        final updated = engine.processSkip(beliefs, skippedHour: 8);
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          greaterThan(10.0),
        );
      });

      test('reduces meetingTolerance when isMeetingAdjacent=true', () {
        final original = beliefs[BeliefParameter.meetingTolerance]!.value; // 0.5
        final updated = engine.processSkip(
          beliefs,
          skippedHour: 14,
          isMeetingAdjacent: true,
        );
        expect(
          updated[BeliefParameter.meetingTolerance]!.value,
          lessThan(original),
        );
      });

      test('does not reduce meetingTolerance when isMeetingAdjacent=false', () {
        final original = beliefs[BeliefParameter.meetingTolerance]!.value;
        final updated = engine.processSkip(
          beliefs,
          skippedHour: 14,
          isMeetingAdjacent: false,
        );
        expect(
          updated[BeliefParameter.meetingTolerance]!.value,
          closeTo(original, 0.0001),
        );
      });
    });

    group('processReschedule', () {
      test('shifts peakEnergy toward newHour', () {
        // default peak=10.0, newHour=16 → should increase
        final updated = engine.processReschedule(beliefs, newHour: 16);
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          greaterThan(10.0),
        );
      });

      test('shifts peakEnergy toward newHour (earlier hour)', () {
        // default peak=10.0, newHour=7 → should decrease
        final updated = engine.processReschedule(beliefs, newHour: 7);
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          lessThan(10.0),
        );
      });

      test('uses weight 0.4 (stronger shift than processTaskCompletion weight 0.3)', () {
        final updatedReschedule = engine.processReschedule(beliefs, newHour: 16);
        final updatedCompletion = engine.processTaskCompletion(
          beliefs,
          taskStartHour: 16,
          durationMinutes: 60,
        );
        // reschedule weight 0.4 should shift more than completion weight 0.3
        final rescheduleDelta = (updatedReschedule[BeliefParameter.peakEnergy]!.value - 10.0).abs();
        final completionDelta = (updatedCompletion[BeliefParameter.peakEnergy]!.value - 10.0).abs();
        expect(rescheduleDelta, greaterThan(completionDelta));
      });
    });

    group('processEnergyReport', () {
      test('updates peakEnergy when level is "great" (energyValue >= 0.7)', () {
        final original = beliefs[BeliefParameter.peakEnergy]!.value; // 10.0
        final updated = engine.processEnergyReport(
          beliefs,
          currentHour: 16,
          level: 'great',
        );
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          isNot(closeTo(original, 0.0001)),
        );
      });

      test('does not update peakEnergy when level is "okay"', () {
        final original = beliefs[BeliefParameter.peakEnergy]!.value;
        final updated = engine.processEnergyReport(
          beliefs,
          currentHour: 16,
          level: 'okay',
        );
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          closeTo(original, 0.0001),
        );
      });

      test('does not update peakEnergy when level is "bad"', () {
        final original = beliefs[BeliefParameter.peakEnergy]!.value;
        final updated = engine.processEnergyReport(
          beliefs,
          currentHour: 16,
          level: 'bad',
        );
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          closeTo(original, 0.0001),
        );
      });

      test('does not update peakEnergy when level is "low"', () {
        final original = beliefs[BeliefParameter.peakEnergy]!.value;
        final updated = engine.processEnergyReport(
          beliefs,
          currentHour: 8,
          level: 'low',
        );
        expect(
          updated[BeliefParameter.peakEnergy]!.value,
          closeTo(original, 0.0001),
        );
      });
    });

    group('decayAll', () {
      test('applies withDecay to all beliefs', () {
        // Create beliefs with old lastUpdated dates to ensure measurable decay
        final oldBeliefs = {
          for (final entry in beliefs.entries)
            entry.key: Belief(
              parameter: entry.value.parameter,
              value: entry.value.value,
              confidence: 0.8,
              lastUpdated: DateTime.now().subtract(const Duration(days: 10)),
              evidenceCount: entry.value.evidenceCount,
            ),
        };

        final decayed = engine.decayAll(oldBeliefs);

        for (final entry in decayed.entries) {
          // confidence should be lower after decay (0.8 - 0.1 = 0.7)
          expect(entry.value.confidence, lessThan(0.8));
        }
      });

      test('decayed confidence floored at 0.2', () {
        final lowBeliefs = {
          for (final entry in beliefs.entries)
            entry.key: Belief(
              parameter: entry.value.parameter,
              value: entry.value.value,
              confidence: 0.21,
              lastUpdated: DateTime.now().subtract(const Duration(days: 30)),
              evidenceCount: 0,
            ),
        };

        final decayed = engine.decayAll(lowBeliefs);

        for (final entry in decayed.entries) {
          expect(entry.value.confidence, greaterThanOrEqualTo(0.2));
        }
      });
    });
  });
}
