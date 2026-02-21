"use client";

import { type CognitiveState } from "@/lib/api";

interface StateIndicatorProps {
  state: CognitiveState;
}

const ENERGY_COLORS = {
  high: "bg-green-500",
  medium: "bg-yellow-500",
  low: "bg-red-500",
};

const LOAD_LABELS = {
  light: "Light load",
  moderate: "Moderate load",
  heavy: "Heavy load",
};

export default function StateIndicator({ state }: StateIndicatorProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-500">
      <span className="flex items-center gap-1.5">
        <span
          className={`w-2 h-2 rounded-full ${ENERGY_COLORS[state.energy_level]}`}
        />
        Energy: {state.energy_level}
      </span>
      <span className="text-zinc-300 dark:text-zinc-700">|</span>
      <span>{LOAD_LABELS[state.load_status]}</span>
    </div>
  );
}
