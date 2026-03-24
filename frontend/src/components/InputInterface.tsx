/**
 * Input Interface - Natural language input with question handling
 */
'use client';

import { useState, FormEvent, KeyboardEvent } from 'react';
import { QuestionResponse } from '@/lib/api';
import styles from './InputInterface.module.css';

interface InputInterfaceProps {
    onSubmit: (input: string) => Promise<void>;
    onAnswer: (hypothesisId: string, parameter: string, value: string) => Promise<void>;
    loading: boolean;
    question?: QuestionResponse | null;
    error?: string | null;
}

export default function InputInterface({
    onSubmit,
    onAnswer,
    loading,
    question,
    error,
}: InputInterfaceProps) {
    const [input, setInput] = useState('');

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        await onSubmit(input);
        setInput('');
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as FormEvent);
        }
    };

    const handleOptionClick = async (value: string) => {
        if (!question) return;
        // Extract parameter from context (simplified for MVP)
        const parameter = question.options[0]?.value.includes('min') ? 'duration' : 'time_preference';
        await onAnswer(question.hypothesis_id, parameter, value);
    };

    return (
        <div className={styles.container}>
            {/* Question UI */}
            {question && (
                <div className={styles.question}>
                    <p className={styles.questionText}>{question.question}</p>
                    <p className={styles.questionContext}>{question.context}</p>
                    <div className={styles.options}>
                        {question.options.map((opt) => (
                            <button
                                key={opt.value}
                                className={styles.option}
                                onClick={() => handleOptionClick(opt.value)}
                                disabled={loading}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Error display */}
            {error && (
                <div className={styles.error}>
                    <span>⚠️</span> {error}
                </div>
            )}

            {/* Main input */}
            <form onSubmit={handleSubmit} className={styles.form}>
                <textarea
                    className={styles.input}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="What would you like to schedule? e.g., 'Deep work on the project for 2 hours'"
                    disabled={loading || !!question}
                    rows={1}
                />
                <button
                    type="submit"
                    className={styles.submit}
                    disabled={loading || !input.trim() || !!question}
                >
                    {loading ? (
                        <span className={styles.spinner} />
                    ) : (
                        <span>→</span>
                    )}
                </button>
            </form>

            <p className={styles.hint}>
                Press Enter to submit • Shift+Enter for new line
            </p>
        </div>
    );
}
