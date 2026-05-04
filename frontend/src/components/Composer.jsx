import { useRef, useEffect } from 'react';

const MAX_CHARS = 1000;

export default function Composer({ value, onChange, onSend, disabled, modelOffline }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  }, [value]);

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim() && !modelOffline) onSend();
    }
  }

  const charsLeft = MAX_CHARS - value.length;
  const nearLimit = charsLeft <= 100;

  return (
    <div className="composer">
      {modelOffline && (
        <div className="offline-banner" role="status">
          Model is offline — chat unavailable
        </div>
      )}
      <div className="composer-inner">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message…"
          maxLength={MAX_CHARS}
          rows={1}
          disabled={disabled || modelOffline}
          aria-label="Message"
        />
        <div className="composer-footer">
          <span className={`char-count ${nearLimit ? 'char-count--warn' : ''}`}>
            {charsLeft}
          </span>
          <button
            className="send-btn"
            onClick={onSend}
            disabled={disabled || !value.trim() || modelOffline}
            type="button"
            aria-label="Send message"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </div>
      <p className="hint">Enter to send · Shift↵ for newline</p>
      <style>{`
        .composer {
          border-top: 1px solid var(--border);
          padding: var(--space-3) var(--space-4);
          flex-shrink: 0;
        }
        .offline-banner {
          font-size: var(--text-sm);
          color: var(--error);
          background: color-mix(in oklch, var(--error) 10%, transparent);
          border-radius: var(--radius-sm);
          padding: var(--space-2) var(--space-3);
          margin-bottom: var(--space-3);
          text-align: center;
        }
        .composer-inner {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
          background: var(--bg-subtle);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: var(--space-3);
          transition: border-color 0.15s;
        }
        .composer-inner:focus-within { border-color: var(--accent); }
        .composer-textarea {
          font-family: var(--font-body);
          font-size: var(--text-base);
          color: var(--text);
          background: transparent;
          border: none;
          resize: none;
          width: 100%;
          min-height: 44px;
          max-height: 160px;
          line-height: 1.5;
          overflow-y: auto;
        }
        .composer-textarea::placeholder { color: var(--text-faint); }
        .composer-textarea:disabled { opacity: 0.6; }
        .composer-footer {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: var(--space-3);
        }
        .char-count {
          font-size: var(--text-xs);
          color: var(--text-faint);
          font-variant-numeric: tabular-nums;
        }
        .char-count--warn { color: var(--error); }
        .send-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          min-width: 44px;
          min-height: 44px;
          background: var(--text);
          color: var(--bg);
          border-radius: var(--radius-sm);
          transition: opacity 0.15s;
          flex-shrink: 0;
        }
        .send-btn:hover:not(:disabled) { opacity: 0.85; }
        .send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
        .hint {
          font-size: var(--text-xs);
          color: var(--text-faint);
          text-align: right;
          padding-top: var(--space-2);
        }
        @media (max-width: 768px) {
          .hint { display: none; }
        }
      `}</style>
    </div>
  );
}
