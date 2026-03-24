/**
 * AI Timebox - Main Application Page
 */
'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';
import { useTimeline, useHumanState, useIntentSubmission, useUndo } from '@/hooks/useTimebox';
import Timeline from '@/components/Timeline';
import InputInterface from '@/components/InputInterface';
import StateIndicator from '@/components/StateIndicator';
import ExplanationDisplay from '@/components/ExplanationDisplay';
import styles from './page.module.css';

export default function Home() {
  const { blocks, loading: timelineLoading, refresh: refreshTimeline } = useTimeline();
  const { state, loading: stateLoading, refresh: refreshState } = useHumanState();
  const { loading, response, error, submit, answer, reset } = useIntentSubmission();
  const { undo } = useUndo();
  const router = useRouter();

  useEffect(() => {
    const isCompleted = localStorage.getItem('onboarding_completed');
    if (!isCompleted) {
      router.push('/onboarding');
    }
  }, [router]);

  const handleSubmit = async (input: string) => {
    await submit(input);
  };

  const handleAnswer = async (hypothesisId: string, parameter: string, value: string) => {
    const result = await answer(hypothesisId, parameter, value);
    if (result.type === 'success') {
      refreshTimeline();
      refreshState();
    }
  };

  const handleUndo = async (undoId: string) => {
    await undo(undoId);
    reset();
    refreshTimeline();
  };

  // Auto-refresh timeline on successful scheduling
  if (response?.type === 'success' && !loading) {
    // Refresh happens via the useEffect in the hook
  }

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>AI Timebox</h1>
          <p className={styles.subtitle}>Cognitive Calendar</p>
        </div>
        <Link href="/onboarding" className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors bg-slate-800/50 px-4 py-2 rounded-lg border border-slate-700/50">
          ✨ Plan My Week
        </Link>
      </header>

      <main className={styles.main}>
        <section className={styles.inputSection}>
          <StateIndicator state={state} loading={stateLoading} />

          {response?.type === 'success' && response.success && (
            <ExplanationDisplay
              success={response.success}
              onUndo={handleUndo}
              onDismiss={() => {
                reset();
                refreshTimeline();
              }}
            />
          )}

          <InputInterface
            onSubmit={handleSubmit}
            onAnswer={handleAnswer}
            loading={loading}
            question={response?.question}
            error={response?.type === 'failure' ? response.failure_reason : error}
          />
        </section>

        <section className={styles.timelineSection}>
          <div className={styles.dateHeader}>
            <h2 className={styles.date}>{today}</h2>
            <button
              className={styles.refreshButton}
              onClick={refreshTimeline}
              disabled={timelineLoading}
            >
              ↻
            </button>
          </div>

          {timelineLoading ? (
            <div className={styles.loading}>Loading...</div>
          ) : (
            <Timeline blocks={blocks} />
          )}
        </section>
      </main>

      <footer className={styles.footer}>
        <p>Protecting your mental energy, one timebox at a time</p>
      </footer>
    </div>
  );
}
