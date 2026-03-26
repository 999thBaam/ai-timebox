import '../models/belief.dart';
import '../models/enums.dart';

class BeliefEngine {
  /// Returns default beliefs for all 6 BeliefParameters at confidence 0.3.
  Map<BeliefParameter, Belief> getDefaultBeliefs() {
    final now = DateTime.now();
    return {
      BeliefParameter.peakEnergy: Belief(
        parameter: BeliefParameter.peakEnergy,
        value: 10.0,
        confidence: 0.3,
        lastUpdated: now,
      ),
      BeliefParameter.deepWorkTolerance: Belief(
        parameter: BeliefParameter.deepWorkTolerance,
        value: 60.0,
        confidence: 0.3,
        lastUpdated: now,
      ),
      BeliefParameter.contextSwitchCost: Belief(
        parameter: BeliefParameter.contextSwitchCost,
        value: 0.5,
        confidence: 0.3,
        lastUpdated: now,
      ),
      BeliefParameter.chaosTolerance: Belief(
        parameter: BeliefParameter.chaosTolerance,
        value: 0.4,
        confidence: 0.3,
        lastUpdated: now,
      ),
      BeliefParameter.meetingTolerance: Belief(
        parameter: BeliefParameter.meetingTolerance,
        value: 0.5,
        confidence: 0.3,
        lastUpdated: now,
      ),
      BeliefParameter.recoveryRate: Belief(
        parameter: BeliefParameter.recoveryRate,
        value: 0.10,
        confidence: 0.3,
        lastUpdated: now,
      ),
    };
  }

  /// Processes a completed task block:
  /// - Updates peakEnergy toward taskStartHour (weight 0.3)
  /// - Updates deepWorkTolerance toward durationMinutes (weight 0.3)
  /// - If minutesSinceLastBlock < 15, reduces contextSwitchCost by 0.15
  Map<BeliefParameter, Belief> processTaskCompletion(
    Map<BeliefParameter, Belief> beliefs, {
    required int taskStartHour,
    required int durationMinutes,
    int? minutesSinceLastBlock,
  }) {
    final updated = Map<BeliefParameter, Belief>.from(beliefs);

    updated[BeliefParameter.peakEnergy] =
        updated[BeliefParameter.peakEnergy]!.update(taskStartHour.toDouble(), 0.3);

    updated[BeliefParameter.deepWorkTolerance] =
        updated[BeliefParameter.deepWorkTolerance]!.update(durationMinutes.toDouble(), 0.3);

    if (minutesSinceLastBlock != null && minutesSinceLastBlock < 15) {
      final current = updated[BeliefParameter.contextSwitchCost]!;
      final newValue = (current.value - 0.15).clamp(0.0, 1.0);
      updated[BeliefParameter.contextSwitchCost] = Belief(
        parameter: current.parameter,
        value: newValue,
        confidence: current.confidence,
        lastUpdated: DateTime.now(),
        evidenceCount: current.evidenceCount + 1,
      );
    }

    return updated;
  }

  /// Processes a skipped task:
  /// - Pushes peakEnergy to opposite hour (hour > 12 → hour-12, else hour+12), weight 0.3
  /// - If isMeetingAdjacent, reduces meetingTolerance by 0.15
  Map<BeliefParameter, Belief> processSkip(
    Map<BeliefParameter, Belief> beliefs, {
    required int skippedHour,
    bool isMeetingAdjacent = false,
  }) {
    final updated = Map<BeliefParameter, Belief>.from(beliefs);

    final oppositeHour = skippedHour > 12 ? skippedHour - 12 : skippedHour + 12;
    updated[BeliefParameter.peakEnergy] =
        updated[BeliefParameter.peakEnergy]!.update(oppositeHour.toDouble(), 0.3);

    if (isMeetingAdjacent) {
      final current = updated[BeliefParameter.meetingTolerance]!;
      final newValue = (current.value - 0.15).clamp(0.0, 1.0);
      updated[BeliefParameter.meetingTolerance] = Belief(
        parameter: current.parameter,
        value: newValue,
        confidence: current.confidence,
        lastUpdated: DateTime.now(),
        evidenceCount: current.evidenceCount + 1,
      );
    }

    return updated;
  }

  /// Processes a reschedule signal:
  /// - Shifts peakEnergy toward newHour with weight 0.4
  Map<BeliefParameter, Belief> processReschedule(
    Map<BeliefParameter, Belief> beliefs, {
    required int newHour,
  }) {
    final updated = Map<BeliefParameter, Belief>.from(beliefs);

    updated[BeliefParameter.peakEnergy] =
        updated[BeliefParameter.peakEnergy]!.update(newHour.toDouble(), 0.4);

    return updated;
  }

  /// Processes an energy level report:
  /// - Only updates peakEnergy if level is "great" (energyValue >= 0.7), weight 0.5
  Map<BeliefParameter, Belief> processEnergyReport(
    Map<BeliefParameter, Belief> beliefs, {
    required int currentHour,
    required String level,
  }) {
    final energyValue = _levelToValue(level);

    if (energyValue >= 0.7) {
      final updated = Map<BeliefParameter, Belief>.from(beliefs);
      updated[BeliefParameter.peakEnergy] =
          updated[BeliefParameter.peakEnergy]!.update(currentHour.toDouble(), 0.5);
      return updated;
    }

    return beliefs;
  }

  /// Applies withDecay to all beliefs in the map.
  Map<BeliefParameter, Belief> decayAll(Map<BeliefParameter, Belief> beliefs) {
    return {
      for (final entry in beliefs.entries)
        entry.key: entry.value.withDecay(),
    };
  }

  double _levelToValue(String level) {
    switch (level.toLowerCase()) {
      case 'great':
        return 1.0;
      case 'good':
        return 0.75;
      case 'okay':
        return 0.5;
      case 'low':
        return 0.3;
      case 'bad':
        return 0.1;
      default:
        return 0.5;
    }
  }
}
