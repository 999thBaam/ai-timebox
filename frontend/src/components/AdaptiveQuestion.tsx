import styles from './AdaptiveQuestion.module.css';

interface Question { id: string; text: string; options: string[]; }
interface Props { question: Question; onAnswer: (questionId: string, answer: string) => void; }

export default function AdaptiveQuestion({ question, onAnswer }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.question}>{question.text}</h2>
      <div className={styles.options}>
        {question.options.map((opt) => (
          <button key={opt} className={styles.option} onClick={() => onAnswer(question.id, opt)}>{opt}</button>
        ))}
      </div>
    </div>
  );
}
