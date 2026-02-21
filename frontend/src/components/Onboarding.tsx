"use client";

import { useState, useEffect } from "react";
import {
  fetchOnboardingQuestions,
  submitOnboarding,
  type OnboardingQuestion,
} from "@/lib/api";

interface OnboardingProps {
  userId: string;
  onComplete: () => void;
}

export default function Onboarding({ userId, onComplete }: OnboardingProps) {
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchOnboardingQuestions()
      .then((qs) => {
        setQuestions(qs);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load questions. Is the backend running?");
        setLoading(false);
      });
  }, []);

  const handleAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await submitOnboarding(userId, answers);
      onComplete();
    } catch {
      setError("Failed to submit. Is the backend running?");
      setSubmitting(false);
    }
  };

  const handleSkip = () => {
    onComplete();
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-zinc-400 animate-pulse">
          Loading questions...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="max-w-md text-center space-y-4">
          <p className="text-red-400">{error}</p>
          <button
            onClick={handleSkip}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 underline"
          >
            Skip onboarding and continue
          </button>
        </div>
      </div>
    );
  }

  const current = questions[currentIndex];
  const isLast = currentIndex === questions.length - 1;
  const progress = ((currentIndex + 1) / questions.length) * 100;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            AI Timebox
          </h1>
          <p className="text-zinc-500 text-sm">
            Let&apos;s calibrate your cognitive profile
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1">
          <div
            className="bg-blue-500 h-1 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Question card */}
        <div className="space-y-6">
          <div className="space-y-2">
            <p className="text-xs text-zinc-400 uppercase tracking-wide">
              {current.category.replace("_", " ")}
            </p>
            <h2 className="text-lg font-medium">{current.question}</h2>
            <p className="text-sm text-zinc-500">{current.context}</p>
          </div>

          {/* Options */}
          <div className="space-y-2">
            {current.options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleAnswer(current.id, opt.value)}
                className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
                  answers[current.id] === opt.value
                    ? "border-blue-500 bg-blue-500/10 text-blue-400"
                    : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center">
          <button
            onClick={handleBack}
            disabled={currentIndex === 0}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Back
          </button>

          <div className="flex gap-3">
            <button
              onClick={handleSkip}
              className="px-4 py-2 text-sm text-zinc-500 hover:text-zinc-300"
            >
              Skip
            </button>

            {isLast ? (
              <button
                onClick={handleSubmit}
                disabled={submitting || Object.keys(answers).length === 0}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? "Setting up..." : "Get Started"}
              </button>
            ) : (
              <button
                onClick={handleNext}
                disabled={!answers[current.id]}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
