import { useState } from 'react';
import { login } from '../lib/api.js';
import { setToken } from '../lib/auth.js';

export default function LoginForm() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!password.trim()) return;
    setLoading(true);
    setError('');
    try {
      const { token } = await login(password);
      setToken(token);
      window.location.href = '/';
    } catch (err) {
      setError(err.message || 'Invalid password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <div className="field">
        <label className="field-label" htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          className="field-input"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="Enter workshop password"
          autoComplete="current-password"
          autoFocus
          disabled={loading}
        />
      </div>
      {error && <p className="field-error" role="alert">{error}</p>}
      <button
        type="submit"
        className="submit-btn"
        disabled={loading || !password.trim()}
      >
        {loading ? 'Signing in…' : 'Enter'}
      </button>
      <style>{`
        .field { display: flex; flex-direction: column; gap: var(--space-2); }
        .field-label {
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--text-muted);
          letter-spacing: 0.02em;
          text-transform: uppercase;
        }
        .field-input {
          font-family: var(--font-body);
          font-size: var(--text-base);
          color: var(--text);
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: var(--space-3) var(--space-4);
          width: 100%;
          transition: border-color 0.15s;
        }
        .field-input:hover { border-color: var(--border-strong); }
        .field-input:focus { border-color: var(--accent); outline: none; }
        .field-input::placeholder { color: var(--text-faint); }
        .field-error {
          font-size: var(--text-sm);
          color: var(--error);
        }
        .submit-btn {
          font-family: var(--font-body);
          font-size: var(--text-base);
          font-weight: 600;
          color: var(--bg);
          background: var(--text);
          border-radius: var(--radius-sm);
          padding: var(--space-3) var(--space-4);
          min-height: 44px;
          width: 100%;
          transition: opacity 0.15s;
        }
        .submit-btn:hover:not(:disabled) { opacity: 0.85; }
        .submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      `}</style>
    </form>
  );
}
