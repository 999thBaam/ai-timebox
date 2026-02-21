"use client";

import { type QuestionResponse } from "@/lib/api";

interface ClarifyingQuestionProps {
  question: QuestionResponse;
  onAnswer: (hypothesisId: string, parameter: string, value: string) => void;
}

export default function ClarifyingQuestion({
  question,
  onAnswer,
}: ClarifyingQuestionProps) {
  // Determine the parameter from the question options context
  const parameter = question.options.length > 0
    ? inferParameter(question)
    : "unknown";

  return (
    <div className="border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 p-4 space-y-3">
      <p className="text-sm font-medium">{question.question}</p>
      <p className="text-xs text-zinc-500">{question.context}</p>
      <div className="flex flex-wrap gap-2">
        {question.options.map((opt) => (
          <button
            key={opt.value}
            onClick={() =>
              onAnswer(question.hypothesis_id, parameter, opt.value)
            }
            className="px-4 py-2 text-sm border border-zinc-300 dark:border-zinc-700 rounded-lg hover:border-blue-500 hover:text-blue-400 transition-colors"
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function inferParameter(question: QuestionResponse): string {
  const text = question.question.toLowerCase();
  if (text.includes("long") || text.includes("duration")) return "duration";
  if (text.includes("when") || text.includes("time")) return "time_preference";
  if (text.includes("who") || text.includes("joining")) return "participants";
  // Fallback: use the first option's value pattern
  return "duration";
}
