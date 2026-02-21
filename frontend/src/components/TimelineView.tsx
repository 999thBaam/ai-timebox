"use client";

import { type TimelineBlock } from "@/lib/api";

interface TimelineViewProps {
  blocks: TimelineBlock[];
}

const ACTIVITY_COLORS: Record<string, string> = {
  DEEP_WORK: "border-l-purple-500 bg-purple-500/5",
  SHALLOW_WORK: "border-l-blue-500 bg-blue-500/5",
  MEETING: "border-l-orange-500 bg-orange-500/5",
  BREAK: "border-l-green-500 bg-green-500/5",
  PERSONAL: "border-l-pink-500 bg-pink-500/5",
  ADMIN: "border-l-zinc-500 bg-zinc-500/5",
};

const ACTIVITY_LABELS: Record<string, string> = {
  DEEP_WORK: "Deep Work",
  SHALLOW_WORK: "Shallow Work",
  MEETING: "Meeting",
  BREAK: "Break",
  PERSONAL: "Personal",
  ADMIN: "Admin",
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function TimelineView({ blocks }: TimelineViewProps) {
  const today = new Date().toLocaleDateString([], {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold tracking-tight">Today&apos;s Schedule</h2>
        <p className="text-xs text-zinc-500">{today}</p>
      </div>

      {blocks.length === 0 ? (
        <div className="text-center py-12 text-zinc-400 text-sm">
          <p>No blocks scheduled yet.</p>
          <p className="text-xs mt-1">
            Type a request to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {blocks.map((block) => (
            <div
              key={block.id}
              className={`border-l-4 rounded-r-lg p-3 space-y-1 ${
                ACTIVITY_COLORS[block.activity_nature] ||
                "border-l-zinc-500 bg-zinc-500/5"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{block.goal}</span>
                {block.is_locked && (
                  <span className="text-xs text-zinc-400" title="Locked">
                    Locked
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <span>
                  {formatTime(block.start_time)} - {formatTime(block.end_time)}
                </span>
                <span className="text-zinc-300 dark:text-zinc-700">|</span>
                <span>
                  {ACTIVITY_LABELS[block.activity_nature] ||
                    block.activity_nature}
                </span>
              </div>
              {(block.buffer_before_minutes > 0 ||
                block.buffer_after_minutes > 0) && (
                <div className="text-xs text-zinc-400">
                  {block.buffer_before_minutes > 0 &&
                    `${block.buffer_before_minutes}min ramp-up`}
                  {block.buffer_before_minutes > 0 &&
                    block.buffer_after_minutes > 0 &&
                    " / "}
                  {block.buffer_after_minutes > 0 &&
                    `${block.buffer_after_minutes}min cool-down`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Time grid hint */}
      {blocks.length > 0 && (
        <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <div className="text-xs text-zinc-400 space-y-1">
            <p>
              {blocks.length} block{blocks.length !== 1 ? "s" : ""} scheduled
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
