import 'package:flutter_test/flutter_test.dart';
import 'package:ai_timebox/models/enums.dart';
import 'package:ai_timebox/models/belief.dart';

void main() {
  group('Belief', () {
    test('update shifts value toward observation', () {
      final belief = Belief(
        parameter: BeliefParameter.deepWorkTolerance,
        value: 0.5,
        confidence: 0.3,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 0,
      );

      final updated = belief.update(1.0, 0.5);

      // new = (0.5*0.3 + 1.0*0.5) / (0.3 + 0.5) = (0.15 + 0.5) / 0.8 = 0.8125
      expect(updated.value, closeTo(0.8125, 0.0001));
    });

    test('update increases confidence', () {
      final belief = Belief(
        parameter: BeliefParameter.contextSwitchCost,
        value: 0.4,
        confidence: 0.3,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 1,
      );

      final updated = belief.update(0.8, 0.5);

      // new_conf = min(0.3 + 0.5*0.1, 0.95) = min(0.35, 0.95) = 0.35
      expect(updated.confidence, closeTo(0.35, 0.0001));
      expect(updated.evidenceCount, 2);
    });

    test('confidence capped at 0.95', () {
      final belief = Belief(
        parameter: BeliefParameter.chaosTolerance,
        value: 0.5,
        confidence: 0.94,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 10,
      );

      final updated = belief.update(0.5, 5.0);

      expect(updated.confidence, closeTo(0.95, 0.0001));
    });

    test('peak energy wraps around 24h — small adjustment (no midnight wrap)', () {
      final belief = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 9.0,
        confidence: 0.3,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 0,
      );

      // observation 10.0, diff = 1.0 <= 12, no wrap
      final updated = belief.update(10.0, 0.5);
      // new = (9.0*0.3 + 10.0*0.5) / (0.3+0.5) = (2.7+5.0)/0.8 = 9.625
      expect(updated.value, closeTo(9.625, 0.0001));
    });

    test('peak energy wraps around midnight (diff > 12)', () {
      final belief = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 23.0,
        confidence: 0.5,
        lastUpdated: DateTime(2026, 3, 26),
        evidenceCount: 2,
      );

      // observation = 1.0. diff = 23.0 - 1.0 = 22 > 12, so adjust obs: 1.0 + 24 = 25.0
      // new = (23.0*0.5 + 25.0*0.5) / (0.5+0.5) = (11.5+12.5)/1.0 = 24.0, mod 24 = 0.0
      final updated = belief.update(1.0, 0.5);
      expect(updated.value, closeTo(0.0, 0.0001));
    });

    test('withDecay reduces confidence over time', () {
      final belief = Belief(
        parameter: BeliefParameter.recoveryRate,
        value: 0.6,
        confidence: 0.8,
        lastUpdated: DateTime(2026, 3, 16), // 10 days ago
        evidenceCount: 5,
      );

      final decayed = belief.withDecay(DateTime(2026, 3, 26));

      // decay = 0.01 * 10 = 0.1, new_conf = 0.8 - 0.1 = 0.7
      expect(decayed.confidence, closeTo(0.7, 0.0001));
      expect(decayed.value, belief.value); // value unchanged
    });

    test('withDecay floors at 0.2', () {
      final belief = Belief(
        parameter: BeliefParameter.meetingTolerance,
        value: 0.5,
        confidence: 0.25,
        lastUpdated: DateTime(2026, 3, 1), // 25 days ago
        evidenceCount: 1,
      );

      final decayed = belief.withDecay(DateTime(2026, 3, 26));

      // decay = 0.01*25=0.25, 0.25-0.25=0.0 < 0.2 → floor to 0.2
      expect(decayed.confidence, closeTo(0.2, 0.0001));
    });

    test('toMap / fromMap roundtrip', () {
      final original = Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 9.0,
        confidence: 0.5,
        lastUpdated: DateTime(2026, 3, 26, 10, 0),
        evidenceCount: 3,
      );

      final map = original.toMap();
      final restored = Belief.fromMap(map);

      expect(restored.parameter, original.parameter);
      expect(restored.value, original.value);
      expect(restored.confidence, original.confidence);
      expect(restored.lastUpdated, original.lastUpdated);
      expect(restored.evidenceCount, original.evidenceCount);
    });
  });
}
