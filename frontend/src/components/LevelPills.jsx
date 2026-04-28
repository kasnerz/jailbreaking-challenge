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
          {level.name}
        </button>
      ))}
      <style>{`
        .level-pills {
          display: flex;
          gap: var(--space-2);
          flex-wrap: wrap;
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
          transition: border-color 0.15s, color 0.15s, background 0.15s;
          cursor: pointer;
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
