import { useState, useEffect } from 'react';
import { fetchHealth } from '../lib/api.js';

export default function GpuStatus() {
  const [status, setStatus] = useState(null); // null = loading

  useEffect(() => {
    async function check() {
      try {
        const data = await fetchHealth();
        setStatus(data.online ? 'online' : 'offline');
      } catch {
        setStatus('offline');
      }
    }
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  if (status === null) return null;

  return (
    <div className="gpu-status" title={status === 'online' ? 'Model online' : 'Model offline'}>
      <span className={`dot dot--${status}`} />
      <span className="label">{status === 'online' ? 'Model online' : 'Model offline'}</span>
      <style>{`
        .gpu-status {
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }
        .dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .dot--online { background: oklch(0.65 0.17 145); }
        .dot--offline { background: var(--error); }
        .label {
          font-size: var(--text-xs);
          color: var(--text-muted);
          white-space: nowrap;
        }
        @media (max-width: 480px) {
          .label { display: none; }
        }
      `}</style>
    </div>
  );
}
