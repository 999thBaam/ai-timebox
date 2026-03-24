/**
 * React hooks for AI Timebox data fetching and state management.
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    parseIntent,
    answerQuestion,
    getTimeline,
    getState,
    getUndoHistory,
    undoChange,
    IntentResponse,
    TimelineBlock,
    HumanStateResponse,
    UndoHistoryItem,
} from '@/lib/api';

// Default user ID for MVP (would come from auth in production)
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001';

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE HOOK
// ═══════════════════════════════════════════════════════════════════════════════

export function useTimeline(date?: string) {
    const [blocks, setBlocks] = useState<TimelineBlock[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getTimeline(DEFAULT_USER_ID, date);
            setBlocks(data.blocks);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load timeline');
        } finally {
            setLoading(false);
        }
    }, [date]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { blocks, loading, error, refresh };
}

// ═══════════════════════════════════════════════════════════════════════════════
// STATE HOOK
// ═══════════════════════════════════════════════════════════════════════════════

export function useHumanState() {
    const [state, setState] = useState<HumanStateResponse | null>(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const data = await getState(DEFAULT_USER_ID);
            setState(data);
        } catch {
            // Silently fail - state is optional UI enhancement
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
        // Refresh every 5 minutes
        const interval = setInterval(refresh, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [refresh]);

    return { state, loading, refresh };
}

// ═══════════════════════════════════════════════════════════════════════════════
// INTENT SUBMISSION HOOK
// ═══════════════════════════════════════════════════════════════════════════════

export function useIntentSubmission() {
    const [loading, setLoading] = useState(false);
    const [response, setResponse] = useState<IntentResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const submit = async (input: string) => {
        setLoading(true);
        setError(null);
        setResponse(null);

        try {
            const result = await parseIntent(DEFAULT_USER_ID, input);
            setResponse(result);
            return result;
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Failed to process request';
            setError(msg);
            throw e;
        } finally {
            setLoading(false);
        }
    };

    const answer = async (hypothesisId: string, parameter: string, value: string) => {
        setLoading(true);
        setError(null);

        try {
            const result = await answerQuestion(hypothesisId, parameter, value);
            setResponse(result);
            return result;
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Failed to process answer';
            setError(msg);
            throw e;
        } finally {
            setLoading(false);
        }
    };

    const reset = () => {
        setResponse(null);
        setError(null);
    };

    return { loading, response, error, submit, answer, reset };
}

// ═══════════════════════════════════════════════════════════════════════════════
// UNDO HOOK
// ═══════════════════════════════════════════════════════════════════════════════

export function useUndo() {
    const [history, setHistory] = useState<UndoHistoryItem[]>([]);
    const [loading, setLoading] = useState(false);

    const refresh = useCallback(async () => {
        try {
            const data = await getUndoHistory(DEFAULT_USER_ID);
            setHistory(data.changes);
        } catch {
            // Silently fail
        }
    }, []);

    const undo = async (changeId: string) => {
        setLoading(true);
        try {
            await undoChange(DEFAULT_USER_ID, changeId);
            await refresh();
            return true;
        } catch {
            return false;
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refresh();
    }, [refresh]);

    return { history, loading, undo, refresh };
}
