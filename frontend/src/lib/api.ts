const API_BASE = "/api";

export interface QuestionOption {
  value: string;
  label: string;
}

export interface OnboardingQuestion {
  id: string;
  category: string;
  question: string;
  context: string;
  options: QuestionOption[];
  required: boolean;
}

export interface ScheduledBlock {
  id: string;
  start_time: string;
  end_time: string;
  goal: string;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
}

export interface TimelineBlock {
  id: string;
  intent_id: string;
  start_time: string;
  end_time: string;
  goal: string;
  activity_nature: string;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  is_locked: boolean;
}

export interface QuestionResponse {
  hypothesis_id: string;
  question: string;
  options: QuestionOption[];
  context: string;
}

export interface SuccessResponse {
  hypothesis_id: string;
  scheduled: ScheduledBlock;
  explanation: string;
  undo_id: string;
}

export interface IntentResponse {
  type: "question" | "success" | "failure";
  question?: QuestionResponse;
  success?: SuccessResponse;
  failure_reason?: string;
}

export interface CognitiveState {
  user_id: string;
  updated_at: string;
  energy_level: "low" | "medium" | "high";
  load_status: "light" | "moderate" | "heavy";
  recommendation: string;
}

export interface TimelineResponse {
  user_id: string;
  date: string;
  blocks: TimelineBlock[];
}

export interface UndoHistoryItem {
  id: string;
  timestamp: string;
  change_type: string;
  description: string;
  can_undo: boolean;
}

// Fetch onboarding questions
export async function fetchOnboardingQuestions(): Promise<OnboardingQuestion[]> {
  const res = await fetch(`${API_BASE}/onboarding/questions`);
  const data = await res.json();
  return data.questions;
}

// Submit onboarding answers
export async function submitOnboarding(
  userId: string,
  answers: Record<string, string>
) {
  const res = await fetch(`${API_BASE}/onboarding/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, answers }),
  });
  return res.json();
}

// Parse an intent (scheduling request)
export async function parseIntent(
  userId: string,
  rawInput: string
): Promise<IntentResponse> {
  const res = await fetch(`${API_BASE}/intents/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, raw_input: rawInput }),
  });
  return res.json();
}

// Answer a clarifying question
export async function answerQuestion(
  hypothesisId: string,
  parameter: string,
  value: string
): Promise<IntentResponse> {
  const res = await fetch(`${API_BASE}/intents/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hypothesis_id: hypothesisId,
      parameter,
      value,
    }),
  });
  return res.json();
}

// Get cognitive state
export async function fetchState(userId: string): Promise<CognitiveState> {
  const res = await fetch(`${API_BASE}/state/${userId}`);
  return res.json();
}

// Get timeline for a date
export async function fetchTimeline(
  userId: string,
  date?: string
): Promise<TimelineResponse> {
  const params = date ? `?target_date=${date}` : "";
  const res = await fetch(`${API_BASE}/timeline/${userId}${params}`);
  return res.json();
}

// Undo a change
export async function undoChange(
  userId: string,
  changeId: string
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/undo/${userId}/undo/${changeId}`, {
    method: "POST",
  });
  return res.json();
}

// Get undo history
export async function fetchUndoHistory(
  userId: string
): Promise<UndoHistoryItem[]> {
  const res = await fetch(`${API_BASE}/undo/${userId}/history`);
  const data = await res.json();
  return data.changes;
}
