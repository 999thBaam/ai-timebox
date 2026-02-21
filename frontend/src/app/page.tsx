"use client";

import { useState, useEffect } from "react";
import Onboarding from "@/components/Onboarding";
import Dashboard from "@/components/Dashboard";

// Generate a stable user ID for this session
function getOrCreateUserId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem("ai-timebox-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("ai-timebox-user-id", id);
  }
  return id;
}

function hasCompletedOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("ai-timebox-onboarded") === "true";
}

export default function Home() {
  const [userId, setUserId] = useState<string>("");
  const [onboarded, setOnboarded] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setUserId(getOrCreateUserId());
    setOnboarded(hasCompletedOnboarding());
    setMounted(true);
  }, []);

  const handleOnboardingComplete = () => {
    localStorage.setItem("ai-timebox-onboarded", "true");
    setOnboarded(true);
  };

  const handleResetOnboarding = () => {
    localStorage.removeItem("ai-timebox-onboarded");
    setOnboarded(false);
  };

  if (!mounted) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-zinc-400">Loading...</div>
      </div>
    );
  }

  if (!onboarded) {
    return (
      <Onboarding userId={userId} onComplete={handleOnboardingComplete} />
    );
  }

  return (
    <Dashboard userId={userId} onResetOnboarding={handleResetOnboarding} />
  );
}
