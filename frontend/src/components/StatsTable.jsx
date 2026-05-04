import { useState, useEffect } from 'react';
import { fetchStats } from '../lib/api.js';
import { getLoginUrl, isAuthenticated } from '../lib/auth.js';

export default function StatsTable() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAuthenticated()) {
      window.location.href = getLoginUrl();
      return;
    }
    fetchStats()
      .then(setStats)
      .catch(err => setError(err.message || 'Failed to load stats'));
  }, []);

  if (error) {
    return <p style={{ color: 'var(--error)', fontSize: 'var(--text-sm)' }}>{error}</p>;
  }

  if (!stats) {
    return <p style={{ color: 'var(--text-faint)', fontSize: 'var(--text-sm)' }}>Loading…</p>;
  }

  if (stats.length === 0) {
    return <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>No attempts yet.</p>;
  }

  return (
    <div className="stats-wrap">
      <table className="stats-table">
        <thead>
          <tr>
            <th>Level</th>
            <th>Attempts</th>
            <th>Successes</th>
            <th>Rate</th>
          </tr>
        </thead>
        <tbody>
          {stats.map(row => (
            <tr key={row.level}>
              <td className="level-cell">{row.level.charAt(0).toUpperCase() + row.level.slice(1)}</td>
              <td>{row.attempts}</td>
              <td>{row.successes}</td>
              <td>{(row.rate * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <style>{`
        .stats-wrap { overflow-x: auto; }
        .stats-table {
          width: 100%;
          border-collapse: collapse;
          font-size: var(--text-sm);
        }
        .stats-table th {
          font-weight: 600;
          color: var(--text-muted);
          text-align: left;
          padding: var(--space-2) var(--space-4) var(--space-3);
          border-bottom: 1px solid var(--border);
          font-size: var(--text-xs);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .stats-table td {
          padding: var(--space-3) var(--space-4);
          color: var(--text);
          border-bottom: 1px solid var(--border);
          font-variant-numeric: tabular-nums;
        }
        .stats-table tr:last-child td { border-bottom: none; }
        .level-cell { font-weight: 500; }
      `}</style>
    </div>
  );
}
