import styles from './RoleSelector.module.css';

const ROLES = [
  { id: 'student', label: 'Student', icon: '📚', desc: 'Classes, study sessions, flexible schedule' },
  { id: 'professional', label: 'Professional', icon: '💼', desc: 'Office hours, meetings, structured day' },
  { id: 'freelancer', label: 'Freelancer', icon: '🎯', desc: 'Client work, self-managed, flexible' },
  { id: 'manager', label: 'Manager', icon: '👥', desc: 'Meetings, coordination, people-focused' },
  { id: 'creative', label: 'Creative', icon: '🎨', desc: 'Deep focus, irregular hours, flow-driven' },
];

interface Props {
  onSelect: (role: string) => void;
  selected: string | null;
}

export default function RoleSelector({ onSelect, selected }: Props) {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>What best describes you?</h2>
      <p className={styles.subtitle}>This helps us set up your schedule. You can always change it later.</p>
      <div className={styles.grid}>
        {ROLES.map((role) => (
          <button
            key={role.id}
            className={`${styles.card} ${selected === role.id ? styles.selected : ''}`}
            onClick={() => onSelect(role.id)}
          >
            <span className={styles.icon}>{role.icon}</span>
            <span className={styles.label}>{role.label}</span>
            <span className={styles.desc}>{role.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
