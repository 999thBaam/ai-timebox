import 'dart:math';
import 'enums.dart';

class Belief {
  final BeliefParameter parameter;
  final double value;
  final double confidence;
  final DateTime lastUpdated;
  final int evidenceCount;

  const Belief({
    required this.parameter,
    required this.value,
    this.confidence = 0.3,
    required this.lastUpdated,
    this.evidenceCount = 0,
  });

  /// Weighted average update.
  /// new_value = (old*conf + obs*weight) / (conf + weight)
  /// For peakEnergy, wraps mod 24 and adjusts observation across midnight if diff > 12.
  /// new_conf = min(conf + weight*0.1, 0.95)
  Belief update(double observation, double signalWeight) {
    double obs = observation;

    if (parameter == BeliefParameter.peakEnergy) {
      final diff = (value - obs).abs();
      if (diff > 12) {
        // adjust observation across midnight
        obs = obs + 24.0;
      }
    }

    final newValue = (value * confidence + obs * signalWeight) /
        (confidence + signalWeight);
    final newConf = min(confidence + signalWeight * 0.1, 0.95);

    double finalValue = newValue;
    if (parameter == BeliefParameter.peakEnergy) {
      finalValue = newValue % 24.0;
    }

    return Belief(
      parameter: parameter,
      value: finalValue,
      confidence: newConf,
      lastUpdated: DateTime.now(),
      evidenceCount: evidenceCount + 1,
    );
  }

  /// Decay confidence 0.01/day since lastUpdated, floor at 0.2.
  Belief withDecay([DateTime? now]) {
    final reference = now ?? DateTime.now();
    final daysSince = reference.difference(lastUpdated).inDays;
    final decayed = max(confidence - 0.01 * daysSince, 0.2);
    return Belief(
      parameter: parameter,
      value: value,
      confidence: decayed,
      lastUpdated: lastUpdated,
      evidenceCount: evidenceCount,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'parameter': parameter.name,
      'value': value,
      'confidence': confidence,
      'last_updated': lastUpdated.millisecondsSinceEpoch,
      'evidence_count': evidenceCount,
    };
  }

  factory Belief.fromMap(Map<String, dynamic> map) {
    return Belief(
      parameter: BeliefParameter.values.byName(map['parameter'] as String),
      value: (map['value'] as num).toDouble(),
      confidence: (map['confidence'] as num).toDouble(),
      lastUpdated:
          DateTime.fromMillisecondsSinceEpoch(map['last_updated'] as int),
      evidenceCount: map['evidence_count'] as int,
    );
  }
}
