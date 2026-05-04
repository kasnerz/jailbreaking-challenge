const LEVEL_ICONS = {
  easy: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
      <path d="m9 12 2 2 4-4"/>
    </svg>
  ),
  medium: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0a5 5 0 0 1 1-3a1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4"/>
    </svg>
  ),
  hard: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12.5 17-.5-1-.5 1z"/>
      <path d="M15 22a1 1 0 0 0 1-1v-1a2 2 0 0 0 1.56-3.25a8 8 0 1 0-11.12 0A2 2 0 0 0 8 20v1a1 1 0 0 0 1 1z"/>
      <circle cx="15" cy="12" r="1" fill="currentColor"/>
      <circle cx="9" cy="12" r="1" fill="currentColor"/>
    </svg>
  ),
};

export default function LevelPills({ levels, activeLevel, onSelect, disabled }) {
  return (
    <div className="level-pills" role="group" aria-label="Difficulty level">
      {levels.map(level => (
        <button
          key={level.id}
          className={`pill ${activeLevel === level.id ? 'pill--active' : ''}`}
          onClick={() => onSelect(level.id)}
          disabled={disabled}
          aria-pressed={activeLevel === level.id}
          title={level.description}
        >
          {LEVEL_ICONS[level.id] && <span className="pill-icon" aria-hidden="true">{LEVEL_ICONS[level.id]}</span>}
          {level.name}
        </button>
      ))}
      <style>{`
        .level-pills {
          display: flex;
          gap: var(--space-2);
          flex-wrap: wrap;
          justify-content: center;
          padding: var(--space-3) var(--space-4);
          border-bottom: 1px solid var(--border);
        }
        .pill {
          font-family: var(--font-body);
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--text-muted);
          background: transparent;
          border: 1px solid var(--border);
          border-radius: 99px;
          padding: var(--space-1) var(--space-4);
          min-height: 32px;
          min-width: 44px;
          display: flex;
          align-items: center;
          gap: var(--space-2);
          transition: border-color 0.15s, color 0.15s, background 0.15s;
          cursor: pointer;
        }
        .pill-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          line-height: 1;
        }
        .pill:hover:not(:disabled) {
          border-color: var(--border-strong);
          color: var(--text);
        }
        .pill--active {
          border-color: var(--accent);
          color: var(--accent);
          background: var(--accent-subtle);
        }
        .pill--active:hover:not(:disabled) {
          border-color: var(--accent-hover);
          color: var(--accent-hover);
        }
        .pill:disabled { opacity: 0.5; cursor: not-allowed; }
      `}</style>
    </div>
  );
}
