/**
 * AI Timebox API Client
 * 
 * Connects frontend to FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface QuestionOption {
    value: string;
    label: string;
}

export interface QuestionResponse {
    hypothesis_id: string;
    question: string;
    options: QuestionOption[];
    context: string;
}

export interface ScheduledBlock {
    id: string;
    start_time: string;
    end_time: string;
    goal: string;
    buffer_before_minutes: number;
    buffer_after_minutes: number;
}

export interface SuccessResponse {
    hypothesis_id: string;
    scheduled: ScheduledBlock;
    explanation: string;
    undo_id: string;
}

export interface IntentResponse {
    type: 'question' | 'success' | 'failure';
    question?: QuestionResponse;
    success?: SuccessResponse;
    failure_reason?: string;
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

export interface TimelineResponse {
    user_id: string;
    date: string;
    blocks: TimelineBlock[];
}

export interface HumanStateResponse {
    user_id: string;
    updated_at: string;
    energy_level: 'low' | 'medium' | 'high';
    load_status: 'light' | 'moderate' | 'heavy';
    recommendation: string;
}

export interface UndoHistoryItem {
    id: string;
    timestamp: string;
    change_type: string;
    description: string;
    can_undo: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export async function parseIntent(userId: string, rawInput: string): Promise<IntentResponse> {
    const res = await fetch(`${API_BASE}/api/intents/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, raw_input: rawInput }),
    });

    if (!res.ok) {
        throw new Error(`Failed to parse intent: ${res.statusText}`);
    }

    return res.json();
}

export async function answerQuestion(
    hypothesisId: string,
    parameter: string,
    value: string
): Promise<IntentResponse> {
    const res = await fetch(`${API_BASE}/api/intents/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            hypothesis_id: hypothesisId,
            parameter,
            value,
        }),
    });

    if (!res.ok) {
        throw new Error(`Failed to answer question: ${res.statusText}`);
    }

    return res.json();
}

export async function getTimeline(
    userId: string,
    date?: string
): Promise<TimelineResponse> {
    const params = new URLSearchParams();
    if (date) params.set('target_date', date);

    const res = await fetch(`${API_BASE}/api/timeline/${userId}?${params}`);

    if (!res.ok) {
        throw new Error(`Failed to get timeline: ${res.statusText}`);
    }

    return res.json();
}

export async function getState(userId: string): Promise<HumanStateResponse> {
    const res = await fetch(`${API_BASE}/api/state/${userId}`);

    if (!res.ok) {
        throw new Error(`Failed to get state: ${res.statusText}`);
    }

    return res.json();
}

export async function getUndoHistory(userId: string): Promise<{ changes: UndoHistoryItem[] }> {
    const res = await fetch(`${API_BASE}/api/undo/${userId}/history`);

    if (!res.ok) {
        throw new Error(`Failed to get undo history: ${res.statusText}`);
    }

    return res.json();
}

export async function undoChange(userId: string, changeId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/api/undo/${userId}/undo/${changeId}`, {
        method: 'POST',
    });

    if (!res.ok) {
        throw new Error(`Failed to undo: ${res.statusText}`);
    }

    return res.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// ONBOARDING API
// ═══════════════════════════════════════════════════════════════════════════════

export interface CreateSessionResponse {
    session_id: string;
    message: string;
}

export interface ChatResponse {
    message: string;
    should_stop: boolean;
    extracted_tasks_count: number;
}

export interface GeneratedScheduleResponse {
    blocks: TimelineBlock[];
    confidence: number;
    has_overflow: boolean;
    overflow_count: number;
}

export async function startOnboardingSession(userId: string): Promise<CreateSessionResponse> {
    const res = await fetch(`${API_BASE}/api/onboarding/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) throw new Error(`Failed to start session: ${res.statusText}`);
    return res.json();
}

export async function updateProfile(
    sessionId: string,
    times: { wake_time: string; sleep_time: string; work_start: string; work_end: string }
): Promise<CreateSessionResponse> {
    const res = await fetch(`${API_BASE}/api/onboarding/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, ...times }),
    });
    if (!res.ok) throw new Error(`Failed to update profile: ${res.statusText}`);
    return res.json();
}

export async function setOnboardingTheme(sessionId: string, theme: string): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/api/onboarding/theme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, theme }),
    });
    if (!res.ok) throw new Error(`Failed to set theme: ${res.statusText}`);
    return res.json();
}

export async function sendOnboardingChat(sessionId: string, message: string): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/api/onboarding/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!res.ok) throw new Error(`Failed to send chat: ${res.statusText}`);
    return res.json();
}

export async function generateSchedule(sessionId: string, date: string): Promise<GeneratedScheduleResponse> {
    const res = await fetch(`${API_BASE}/api/onboarding/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, date }),
    });
    if (!res.ok) throw new Error(`Failed to generate schedule: ${res.statusText}`);
    return res.json();
}
