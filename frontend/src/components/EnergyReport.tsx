'use client';
import { useState, useEffect } from 'react';
import styles from './EnergyReport.module.css';

interface Props {
  blockId: string;
  onReport: (blockId: string, level: string) => void;
  onDismiss: () => void;
}

export default function EnergyReport({ blockId, onReport, onDismiss }: Props) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => { setVisible(false); onDismiss(); }, 10000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  if (!visible) return null;

  return (
    <div className={styles.container}>
      <span className={styles.label}>How do you feel?</span>
      <div className={styles.buttons}>
        <button className={styles.btn} onClick={() => onReport(blockId, 'low')}>Low</button>
        <button className={styles.btn} onClick={() => onReport(blockId, 'ok')}>OK</button>
        <button className={styles.btn} onClick={() => onReport(blockId, 'great')}>Great</button>
      </div>
    </div>
  );
}
