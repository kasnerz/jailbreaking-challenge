export default function ChatMessage({ role, content, isStreaming, status }) {
  // status: 'success' | 'failure' | null
  // Highlight secret word in response — we don't know it client-side, but the backend
  // sends success=true in the done event; we add a visual "Success" badge inline.

  return (
    <div className={`message message--${role}`}>
      <div className="message-meta">
        <span className="message-role">{role === 'user' ? 'You' : 'AI'}</span>
        {status === 'success' && (
          <span className="badge badge--success">Secret revealed</span>
        )}
        {status === 'failure' && (
          <span className="badge badge--failure">Not yet</span>
        )}
      </div>
      <div className={`message-body ${role === 'assistant' ? 'message-body--mono' : ''}`}>
        {content}
        {isStreaming && <span className="cursor" aria-hidden="true" />}
      </div>
      <style>{`
        .message {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
          padding: var(--space-4) 0;
        }
        .message + .message {
          border-top: 1px solid var(--border);
        }
        .message-meta {
          display: flex;
          align-items: center;
          gap: var(--space-3);
        }
        .message-role {
          font-size: var(--text-xs);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--text-faint);
        }
        .message--user .message-role { color: var(--text-muted); }
        .message-body {
          font-size: var(--text-base);
          color: var(--text);
          line-height: 1.65;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .message-body--mono {
          font-family: var(--font-mono);
          font-size: var(--text-sm);
          line-height: 1.7;
        }
        .cursor {
          display: inline-block;
          width: 2px;
          height: 1em;
          background: var(--accent);
          margin-left: 2px;
          vertical-align: text-bottom;
          animation: blink 1s step-end infinite;
        }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        .badge {
          font-size: var(--text-xs);
          font-weight: 500;
          padding: 2px var(--space-2);
          border-radius: 4px;
          letter-spacing: 0.02em;
        }
        .badge--success {
          color: var(--accent);
          background: var(--accent-subtle);
        }
        .badge--failure {
          color: var(--text-faint);
          background: var(--bg-subtle);
        }
      `}</style>
    </div>
  );
}
