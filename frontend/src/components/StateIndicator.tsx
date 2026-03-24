/**
 * State Indicator - Shows user's cognitive state
 */
'use client';

import { HumanStateResponse } from '@/lib/api';
import styles from './StateIndicator.module.css';

interface StateIndicatorProps {
    state: HumanStateResponse | null;
    loading: boolean;
}

function getEnergyEmoji(level: string): string {
    const emojis: Record<string, string> = {
        low: '🔋',
        medium: '⚡',
        high: '✨',
    };
    return emojis[level] || '⚡';
}

function getLoadColor(status: string): string {
    const colors: Record<string, string> = {
        light: '#10b981',    // Green
        moderate: '#f59e0b', // Amber
        heavy: '#ef4444',    // Red
    };
    return colors[status] || colors.moderate;
}

export default function StateIndicator({ state, loading }: StateIndicatorProps) {
    if (loading || !state) {
        return (
            <div className={styles.container}>
                <div className={styles.skeleton} />
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.indicator}>
                <div className={styles.energy}>
                    <span className={styles.emoji}>{getEnergyEmoji(state.energy_level)}</span>
                    <span className={styles.label}>{state.energy_level} energy</span>
                </div>

                <div className={styles.divider} />

                <div
                    className={styles.load}
                    style={{ '--load-color': getLoadColor(state.load_status) } as React.CSSProperties}
                >
                    <span
                        className={styles.dot}
                    />
                    <span className={styles.label}>{state.load_status} load</span>
                </div>
            </div>

            <p className={styles.recommendation}>{state.recommendation}</p>
        </div>
    );
}
