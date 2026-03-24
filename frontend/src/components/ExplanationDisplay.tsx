/**
 * Explanation Display - Shows scheduling explanation with undo
 */
'use client';

import { SuccessResponse } from '@/lib/api';
import styles from './ExplanationDisplay.module.css';

interface ExplanationDisplayProps {
    success: SuccessResponse;
    onUndo: (undoId: string) => Promise<void>;
    onDismiss: () => void;
}

function formatTime(isoString: string): string {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

export default function ExplanationDisplay({
    success,
    onUndo,
    onDismiss,
}: ExplanationDisplayProps) {
    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <span className={styles.icon}>✓</span>
                <span className={styles.title}>Scheduled</span>
                <button className={styles.dismiss} onClick={onDismiss}>×</button>
            </div>

            <div className={styles.scheduled}>
                <h3 className={styles.goal}>{success.scheduled.goal}</h3>
                <p className={styles.time}>
                    {formatTime(success.scheduled.start_time)} – {formatTime(success.scheduled.end_time)}
                </p>
            </div>

            <p className={styles.explanation}>{success.explanation}</p>

            <div className={styles.actions}>
                <button
                    className={styles.undo}
                    onClick={() => onUndo(success.undo_id)}
                >
                    ↶ Undo
                </button>
            </div>
        </div>
    );
}
