import styles from './ProfileSummary.module.css';

interface Props { summary: string; onContinue: () => void; }

export default function ProfileSummary({ summary, onContinue }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Your Profile</h2>
      <p className={styles.summary}>{summary}</p>
      <button className={styles.button} onClick={onContinue}>Continue</button>
    </div>
  );
}
