/**
 * Timeline Component - Visual representation of scheduled blocks
 */
'use client';

import { TimelineBlock } from '@/lib/api';
import styles from './Timeline.module.css';

interface TimelineProps {
    blocks: TimelineBlock[];
    onUndo?: (blockId: string) => void;
}

function formatTime(isoString: string): string {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

function getActivityColor(nature: string): string {
    const colors: Record<string, string> = {
        DEEP_WORK: '#6366f1',    // Indigo
        SHALLOW_WORK: '#8b5cf6', // Violet
        MEETING: '#f59e0b',      // Amber
        BREAK: '#10b981',        // Emerald
        PERSONAL: '#ec4899',     // Pink
        ADMIN: '#64748b',        // Slate
    };
    return colors[nature] || colors.SHALLOW_WORK;
}

function getDuration(start: string, end: string): number {
    return Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
}

export default function Timeline({ blocks, onUndo }: TimelineProps) {
    if (blocks.length === 0) {
        return (
            <div className={styles.empty}>
                <div className={styles.emptyIcon}>📅</div>
                <p>No events scheduled for today</p>
                <p className={styles.emptyHint}>Type what you want to do above</p>
            </div>
        );
    }

    return (
        <div className={styles.timeline}>
            {blocks.map((block) => (
                <div
                    key={block.id}
                    className={styles.block}
                    style={{ '--block-color': getActivityColor(block.activity_nature) } as React.CSSProperties}
                >
                    <div className={styles.time}>
                        <span className={styles.startTime}>{formatTime(block.start_time)}</span>
                        <span className={styles.duration}>{getDuration(block.start_time, block.end_time)} min</span>
                    </div>

                    <div className={styles.content}>
                        <div className={styles.colorBar} />
                        <div className={styles.details}>
                            <h3 className={styles.goal}>{block.goal}</h3>
                            <div className={styles.meta}>
                                <span className={styles.nature}>
                                    {block.activity_nature.replace('_', ' ')}
                                </span>
                                {block.buffer_before_minutes > 0 && (
                                    <span className={styles.buffer}>
                                        {block.buffer_before_minutes}m ramp-up
                                    </span>
                                )}
                                {block.is_locked && (
                                    <span className={styles.locked}>🔒</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
