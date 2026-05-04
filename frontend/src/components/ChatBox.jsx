import { useState, useEffect, useRef, useCallback } from 'react';
import { getLoginUrl, isAuthenticated } from '../lib/auth.js';
import { fetchLevels, fetchHealth, streamChat } from '../lib/api.js';
import LevelPills from './LevelPills.jsx';
import ChatMessage from './ChatMessage.jsx';
import Composer from './Composer.jsx';

export default function ChatBox() {
  const [levels, setLevels] = useState([]);
  const [activeLevel, setActiveLevel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [modelOffline, setModelOffline] = useState(false);
  const [input, setInput] = useState('');
  const [glowing, setGlowing] = useState(false);
  // Track status per message index
  const [messageStatus, setMessageStatus] = useState({}); // index -> 'success'|'failure'|null
  const scrollRef = useRef(null);

  // Auth guard
  useEffect(() => {
    if (!isAuthenticated()) {
      window.location.href = getLoginUrl();
    }
  }, []);

  // Load levels
  useEffect(() => {
    fetchLevels().then(data => {
      setLevels(data);
      if (data.length > 0) setActiveLevel(data[0].id);
    }).catch(console.error);
  }, []);

  // Health polling
  useEffect(() => {
    async function check() {
      try {
        const { online } = await fetchHealth();
        setModelOffline(!online);
      } catch {
        setModelOffline(true);
      }
    }
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  // Scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  function handleLevelChange(levelId) {
    if (levelId === activeLevel) return;
    setActiveLevel(levelId);
    setMessages([]);
    setMessageStatus({});
  }

  const handleSend = useCallback(async () => {
    if (!input.trim() || streaming || modelOffline) return;
    const prompt = input.trim();
    setInput('');
    setStreaming(true);

    // Append user message and placeholder assistant message
    const userMsg = { role: 'user', content: prompt };
    const assistantMsg = { role: 'assistant', content: '' };

    // Capture current history before appending
    let history;
    setMessages(prev => {
      history = prev.map(m => ({ role: m.role, content: m.content }));
      return [...prev, userMsg, assistantMsg];
    });

    // Wait for state to update and get the history snapshot
    // history may still be undefined if setMessages hasn't run synchronously
    // Use messages ref captured before state update
    const currentHistory = history ?? messages.map(m => ({ role: m.role, content: m.content }));

    try {
      const { success } = await streamChat(
        activeLevel,
        currentHistory,
        prompt,
        (token) => {
          setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: updated[lastIdx].content + token,
            };
            return updated;
          });
        }
      );

      // Set message status on the assistant message
      setMessages(prev => {
        const lastIdx = prev.length - 1;
        setMessageStatus(s => ({ ...s, [lastIdx]: success ? 'success' : 'failure' }));
        return prev;
      });

      if (success) {
        setGlowing(true);
        setTimeout(() => setGlowing(false), 1600);
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        updated[lastIdx] = { ...updated[lastIdx], content: `Error: ${err.message}` };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  }, [input, streaming, modelOffline, activeLevel, messages]);

  const activeLastAssistantIdx = streaming
    ? messages.length - 1
    : null;

  return (
    <div className={`chatbox ${glowing ? 'chatbox--success' : ''}`}>
      <LevelPills
        levels={levels}
        activeLevel={activeLevel}
        onSelect={handleLevelChange}
        disabled={streaming}
      />
      <div className="message-thread" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Send a message to begin. Good luck.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            role={msg.role}
            content={msg.content}
            isStreaming={i === activeLastAssistantIdx}
            status={messageStatus[i] ?? null}
          />
        ))}
      </div>
      <Composer
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={streaming}
        modelOffline={modelOffline}
      />
      <style>{`
        .chatbox {
          width: 100%;
          max-width: 700px;
          height: calc(100dvh - 180px);
          min-height: 400px;
          display: flex;
          flex-direction: column;
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius-xl);
          overflow: hidden;
          transition: border-color 0.3s, box-shadow 0.3s;
        }
        .chatbox--success {
          border-color: var(--accent);
          box-shadow: 0 0 0 3px var(--accent-glow), 0 0 32px var(--accent-glow);
          animation: success-pulse 1.6s ease-out forwards;
        }
        @keyframes success-pulse {
          0% { box-shadow: 0 0 0 3px var(--accent-glow), 0 0 40px var(--accent-glow); border-color: var(--accent); }
          60% { box-shadow: 0 0 0 2px var(--accent-glow), 0 0 24px var(--accent-glow); border-color: var(--accent); }
          100% { box-shadow: none; border-color: var(--border); }
        }
        .message-thread {
          flex: 1;
          overflow-y: auto;
          padding: var(--space-4);
          scroll-behavior: smooth;
        }
        .empty-state {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .empty-state p {
          font-size: var(--text-sm);
          color: var(--text-faint);
          text-align: center;
        }
        @media (max-width: 768px) {
          .chatbox {
            border-radius: var(--radius-lg);
            height: calc(100dvh - 160px);
          }
        }
        @media (max-width: 480px) {
          .chatbox {
            border-radius: var(--radius-md);
            height: calc(100dvh - 140px);
          }
        }
      `}</style>
    </div>
  );
}
