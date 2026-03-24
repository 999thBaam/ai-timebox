'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    startOnboardingSession,
    updateProfile,
    setOnboardingTheme,
    sendOnboardingChat,
    generateSchedule,
    TimelineBlock
} from '@/lib/api';
import Timeline from '@/components/Timeline';

export default function OnboardingPage() {
    const router = useRouter();
    const [phase, setPhase] = useState<'init' | 'form' | 'theme' | 'chat' | 'preview'>('init');
    const [sessionId, setSessionId] = useState<string>('');
    const [loading, setLoading] = useState(false);

    // Form State
    const [form, setForm] = useState({
        wake_time: '07:00',
        sleep_time: '23:00',
        work_start: '09:00',
        work_end: '17:00',
    });

    // Theme State
    const [theme, setTheme] = useState('');

    // Chat State
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
    const [input, setInput] = useState('');
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Preview State
    const [schedule, setSchedule] = useState<TimelineBlock[]>([]);

    // Start session on mount
    useEffect(() => {
        const initSession = async () => {
            try {
                // Hardcoded user ID for MVP
                const res = await startOnboardingSession('00000000-0000-0000-0000-000000000001');
                setSessionId(res.session_id);
                setPhase('form');
            } catch (e) {
                console.error(e);
            }
        };
        initSession();
    }, []);

    // Auto-scroll chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleFormSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await updateProfile(sessionId, form);
            setPhase('theme');
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleThemeSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await setOnboardingTheme(sessionId, theme);
            setMessages([
                { role: 'assistant', content: res.message }
            ]);
            setPhase('chat');
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleChatSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await sendOnboardingChat(sessionId, userMsg);
            setMessages(prev => [...prev, { role: 'assistant', content: res.message }]);

            if (res.should_stop) {
                // Generate schedule automatically
                generateDraftSchedule();
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const generateDraftSchedule = async () => {
        setLoading(true);
        try {
            // Use tomorrow's date for demo
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const dateStr = tomorrow.toISOString().split('T')[0];

            const res = await generateSchedule(sessionId, dateStr);
            setSchedule(res.blocks);
            setPhase('preview');
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-2xl bg-slate-900/50 p-8 rounded-2xl border border-slate-800 shadow-xl backdrop-blur-sm">

                {/* Header */}
                <div className="mb-8 text-center">
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                        Setup Your Cognitive Calendar
                    </h1>
                    <div className="flex justify-center gap-2 mt-4">
                        <Step active={phase === 'form'} done={phase !== 'init' && phase !== 'form'} />
                        <Step active={phase === 'theme'} done={phase === 'chat' || phase === 'preview'} />
                        <Step active={phase === 'chat'} done={phase === 'preview'} />
                        <Step active={phase === 'preview'} done={false} />
                    </div>
                </div>

                {/* Content */}
                {phase === 'init' && (
                    <div className="text-center py-12 text-slate-400">Initializing...</div>
                )}

                {phase === 'form' && (
                    <form onSubmit={handleFormSubmit} className="space-y-6">
                        <div className="grid grid-cols-2 gap-6">
                            <TimeInput label="Wake Up" value={form.wake_time} onChange={v => setForm({ ...form, wake_time: v })} />
                            <TimeInput label="Sleep" value={form.sleep_time} onChange={v => setForm({ ...form, sleep_time: v })} />
                            <TimeInput label="Work Start" value={form.work_start} onChange={v => setForm({ ...form, work_start: v })} />
                            <TimeInput label="Work End" value={form.work_end} onChange={v => setForm({ ...form, work_end: v })} />
                        </div>
                        <Button loading={loading}>Next: Set Context →</Button>
                    </form>
                )}

                {phase === 'theme' && (
                    <form onSubmit={handleThemeSubmit} className="space-y-6">
                        <div>
                            <label className="block text-slate-400 text-sm mb-2">What is your main theme for this week?</label>
                            <input
                                type="text"
                                className="w-full bg-slate-800 border-none rounded-xl p-4 text-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                                placeholder="e.g., Shipping MVP, Recovering from burnout, Clearing backlog..."
                                value={theme}
                                onChange={e => setTheme(e.target.value)}
                                autoFocus
                            />
                        </div>
                        <Button loading={loading}>Start Planning →</Button>
                    </form>
                )}

                {phase === 'chat' && (
                    <div className="flex flex-col h-[500px]">
                        <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4">
                            {messages.map((m, i) => (
                                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[80%] p-4 rounded-2xl ${m.role === 'user'
                                            ? 'bg-indigo-600 text-white rounded-br-none'
                                            : 'bg-slate-800 text-slate-200 rounded-bl-none'
                                        }`}>
                                        {m.content}
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="bg-slate-800 p-4 rounded-2xl rounded-bl-none text-slate-400 animate-pulse">
                                        Thinking...
                                    </div>
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                        <form onSubmit={handleChatSubmit} className="flex gap-2">
                            <input
                                type="text"
                                className="flex-1 bg-slate-800 border-none rounded-xl p-4 focus:ring-2 focus:ring-indigo-500 outline-none"
                                placeholder="Type a task..."
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                autoFocus
                            />
                            <button
                                type="submit"
                                disabled={loading || !input.trim()}
                                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white p-4 rounded-xl transition-colors"
                            >
                                Send
                            </button>
                        </form>
                    </div>
                )}

                {phase === 'preview' && (
                    <div className="space-y-6">
                        <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                            <h2 className="text-lg font-medium text-slate-200 mb-2">Review Your Draft Schedule</h2>
                            <p className="text-slate-400 text-sm">
                                Based on your inputs, here is a suggested plan for tomorrow.
                                We placed your highest priority work during your peak energy hours.
                            </p>
                        </div>

                        <div className="max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                            <Timeline blocks={schedule} />
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => router.push('/')}
                                className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-3 rounded-xl transition-colors border border-slate-700"
                            >
                                Edit Later
                            </button>
                            <button
                                onClick={() => router.push('/')}
                                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl transition-colors font-medium"
                            >
                                Confirm Plan ✨
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </main>
    );
}

// Components

function Step({ active, done }: { active: boolean; done: boolean }) {
    return (
        <div className={`h-1 flex-1 rounded-full transition-colors ${active ? 'bg-indigo-500' : done ? 'bg-indigo-900' : 'bg-slate-800'
            }`} />
    );
}

function TimeInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-slate-400 text-xs uppercase font-bold tracking-wider mb-2">{label}</label>
            <input
                type="time"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                value={value}
                onChange={e => onChange(e.target.value)}
            />
        </div>
    );
}

function Button({ children, loading, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
    return (
        <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-4 rounded-xl transition-all active:scale-[0.98]"
            {...props}
        >
            {loading ? 'Processing...' : children}
        </button>
    );
}
