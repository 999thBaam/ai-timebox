'use client';
import styles from './CheckInCard.module.css';

interface Props {
  question: string;
  options: string[];
  parameter: string;
  onAnswer: (parameter: string, answer: string) => void;
  onDismiss: () => void;
}

export default function CheckInCard({ question, options, parameter, onAnswer, onDismiss }: Props) {
  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <h3 className={styles.title}>Weekly Check-in</h3>
        <p className={styles.question}>{question}</p>
        <div className={styles.options}>
          {options.map((opt) => (
            <button key={opt} className={styles.option} onClick={() => onAnswer(parameter, opt)}>{opt}</button>
          ))}
        </div>
        <button className={styles.dismiss} onClick={onDismiss}>Skip this week</button>
      </div>
    </div>
  );
}
