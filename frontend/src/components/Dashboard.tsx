"use client";

import { useState, useEffect, useCallback } from "react";
import {
  parseIntent,
  answerQuestion,
  fetchState,
  fetchTimeline,
  undoChange,
  type IntentResponse,
  type CognitiveState,
  type TimelineBlock,
  type QuestionResponse,
} from "@/lib/api";
import TimelineView from "./TimelineView";
import StateIndicator from "./StateIndicator";
import ClarifyingQuestion from "./ClarifyingQuestion";

interface DashboardProps {
  userId: string;
  onResetOnboarding: () => void;
}

interface HistoryEntry {
  type: "user" | "system" | "error";
  text: string;
  undoId?: string;
}

export default function Dashboard({ userId, onResetOnboarding }: DashboardProps) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [state, setState] = useState<CognitiveState | null>(null);
  const [blocks, setBlocks] = useState<TimelineBlock[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<QuestionResponse | null>(null);

  const refreshData = useCallback(async () => {
    try {
      const [stateData, timelineData] = await Promise.all([
        fetchState(userId),
        fetchTimeline(userId),
      ]);
      setState(stateData);
      setBlocks(timelineData.blocks);
    } catch {
      // Backend might not be running yet
    }
  }, [userId]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userInput = input.trim();
    setInput("");
    setHistory((h) => [...h, { type: "user", text: userInput }]);
    setLoading(true);

    try {
      const response = await parseIntent(userId, userInput);
      handleResponse(response);
    } catch {
      setHistory((h) => [
        ...h,
        { type: "error", text: "Could not reach the backend. Is it running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleResponse = (response: IntentResponse) => {
    if (response.type === "question" && response.question) {
      setPendingQuestion(response.question);
      setHistory((h) => [
        ...h,
        { type: "system", text: response.question!.context },
      ]);
    } else if (response.type === "success" && response.success) {
      const s = response.success;
      const start = new Date(s.scheduled.start_time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      const end = new Date(s.scheduled.end_time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      setHistory((h) => [
        ...h,
        {
          type: "system",
          text: `Scheduled "${s.scheduled.goal}" from ${start} to ${end}. ${s.explanation}`,
          undoId: s.undo_id,
        },
      ]);
      refreshData();
    } else if (response.type === "failure") {
      setHistory((h) => [
        ...h,
        {
          type: "error",
          text: response.failure_reason || "Could not schedule this request.",
        },
      ]);
    }
  };

  const handleQuestionAnswer = async (
    hypothesisId: string,
    parameter: string,
    value: string
  ) => {
    setPendingQuestion(null);
    setLoading(true);

    try {
      const response = await answerQuestion(hypothesisId, parameter, value);
      handleResponse(response);
    } catch {
      setHistory((h) => [
        ...h,
        { type: "error", text: "Failed to process answer." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleUndo = async (undoId: string) => {
    try {
      const result = await undoChange(userId, undoId);
      if (result.success) {
        setHistory((h) => [...h, { type: "system", text: "Change undone." }]);
        refreshData();
      }
    } catch {
      setHistory((h) => [...h, { type: "error", text: "Failed to undo." }]);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">AI Timebox</h1>
          {state && <StateIndicator state={state} />}
        </div>
        <button
          onClick={onResetOnboarding}
          className="text-xs text-zinc-400 hover:text-zinc-300"
        >
          Recalibrate
        </button>
      </header>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left: Chat / Input */}
        <div className="flex-1 flex flex-col border-r border-zinc-200 dark:border-zinc-800">
          {/* History */}
          <div className="flex-1 overflow-y-auto p-6 space-y-3">
            {history.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-3 text-zinc-400">
                <p className="text-lg">What would you like to schedule?</p>
                <div className="text-sm space-y-1">
                  <p>Try something like:</p>
                  <p className="text-zinc-500">
                    &quot;Write code for 2 hours this morning&quot;
                  </p>
                  <p className="text-zinc-500">
                    &quot;Team meeting at 3pm&quot;
                  </p>
                  <p className="text-zinc-500">
                    &quot;Take a 15 minute break&quot;
                  </p>
                </div>
              </div>
            )}

            {history.map((entry, i) => (
              <div key={i} className="flex flex-col gap-1">
                <div
                  className={`rounded-lg px-4 py-2 max-w-[85%] text-sm ${
                    entry.type === "user"
                      ? "ml-auto bg-blue-600 text-white"
                      : entry.type === "error"
                        ? "bg-red-500/10 text-red-400 border border-red-500/20"
                        : "bg-zinc-100 dark:bg-zinc-800/50 text-zinc-700 dark:text-zinc-300"
                  }`}
                >
                  {entry.text}
                </div>
                {entry.undoId && (
                  <button
                    onClick={() => handleUndo(entry.undoId!)}
                    className="text-xs text-zinc-400 hover:text-blue-400 self-start ml-1"
                  >
                    Undo
                  </button>
                )}
              </div>
            ))}

            {loading && (
              <div className="bg-zinc-100 dark:bg-zinc-800/50 rounded-lg px-4 py-2 max-w-[85%] text-sm text-zinc-400 animate-pulse">
                Thinking...
              </div>
            )}
          </div>

          {/* Clarifying question */}
          {pendingQuestion && (
            <ClarifyingQuestion
              question={pendingQuestion}
              onAnswer={handleQuestionAnswer}
            />
          )}

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="border-t border-zinc-200 dark:border-zinc-800 p-4"
          >
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What do you want to schedule?"
                className="flex-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg px-4 py-2.5 text-sm placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                disabled={loading || !!pendingQuestion}
              />
              <button
                type="submit"
                disabled={loading || !input.trim() || !!pendingQuestion}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Schedule
              </button>
            </div>
          </form>
        </div>

        {/* Right: Timeline */}
        <div className="w-full lg:w-96 p-6 overflow-y-auto">
          <TimelineView blocks={blocks} />
        </div>
      </div>
    </div>
  );
}
