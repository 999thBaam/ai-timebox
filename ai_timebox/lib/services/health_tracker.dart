enum HealthPhase {
  silent,
  gentleNudge,
  patternForming,
  habitBuilding,
  adapted,
}

class HealthTracker {
  final int appDayCount;
  final int acceptedNudgesThisWeek;
  final bool skippedFullWeek;

  const HealthTracker({
    required this.appDayCount,
    this.acceptedNudgesThisWeek = 0,
    this.skippedFullWeek = false,
  });

  /// Returns the current engagement phase based on usage history.
  ///
  /// Priority order:
  /// 1. If skippedFullWeek → gentleNudge (re-engagement)
  /// 2. appDayCount <= 3 → silent
  /// 3. appDayCount <= 7 → gentleNudge
  /// 4. appDayCount <= 21 → patternForming if acceptedNudgesThisWeek >= 2, else gentleNudge
  /// 5. appDayCount <= 60 → habitBuilding
  /// 6. else → adapted
  HealthPhase get currentPhase {
    if (skippedFullWeek) return HealthPhase.gentleNudge;
    if (appDayCount <= 3) return HealthPhase.silent;
    if (appDayCount <= 7) return HealthPhase.gentleNudge;
    if (appDayCount <= 21) {
      return acceptedNudgesThisWeek >= 2
          ? HealthPhase.patternForming
          : HealthPhase.gentleNudge;
    }
    if (appDayCount <= 60) return HealthPhase.habitBuilding;
    return HealthPhase.adapted;
  }

  /// Returns true unless we are in the silent phase.
  bool get shouldSuggest => currentPhase != HealthPhase.silent;
}
