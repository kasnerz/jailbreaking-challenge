import { useState, useEffect, useRef, useCallback } from 'react';
import { getLoginUrl, isAuthenticated } from '../lib/auth.js';
import { fetchLevels, fetchHealth, streamChat } from '../lib/api.js';
import LevelPills from './LevelPills.jsx';
import ChatMessage from './ChatMessage.jsx';
import Composer from './Composer.jsx';

const CHAT_SESSION_KEY = 'jailbreaking_chat_session';

function readPersistedSession() {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const raw = window.sessionStorage.getItem(CHAT_SESSION_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    return {
      activeLevel: typeof parsed.activeLevel === 'string' ? parsed.activeLevel : null,
      messages: Array.isArray(parsed.messages)
        ? parsed.messages.filter(message =>
            message
            && (message.role === 'user' || message.role === 'assistant')
            && typeof message.content === 'string'
          )
        : [],
      input: typeof parsed.input === 'string' ? parsed.input : '',
      messageStatus: parsed.messageStatus && typeof parsed.messageStatus === 'object'
        ? parsed.messageStatus
        : {},
    };
  } catch {
    window.sessionStorage.removeItem(CHAT_SESSION_KEY);
    return null;
  }
}

function clearPersistedSession() {
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(CHAT_SESSION_KEY);
  }
}

export default function ChatBox() {
  const persistedSession = readPersistedSession();
  const [levels, setLevels] = useState([]);
  const [activeLevel, setActiveLevel] = useState(persistedSession?.activeLevel ?? null);
  const [messages, setMessages] = useState(persistedSession?.messages ?? []);
  const [streaming, setStreaming] = useState(false);
  const [modelOffline, setModelOffline] = useState(false);
  const [input, setInput] = useState(persistedSession?.input ?? '');
  const [glowing, setGlowing] = useState(false);
  // Track status per message index
  const [messageStatus, setMessageStatus] = useState(persistedSession?.messageStatus ?? {}); // index -> 'success'|'failure'|null
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
      if (data.length === 0) {
        return;
      }

      setActiveLevel(currentLevel => {
        if (currentLevel && data.some(level => level.id === currentLevel)) {
          return currentLevel;
        }

        return data[0].id;
      });
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

  useEffect(() => {
    if (!activeLevel && messages.length === 0 && !input && Object.keys(messageStatus).length === 0) {
      clearPersistedSession();
      return;
    }

    window.sessionStorage.setItem(CHAT_SESSION_KEY, JSON.stringify({
      activeLevel,
      messages,
      input,
      messageStatus,
    }));
  }, [activeLevel, input, messageStatus, messages]);

  const resetChat = useCallback(() => {
    setMessages([]);
    setMessageStatus({});
    setInput('');
    clearPersistedSession();
  }, []);

  function handleLevelChange(levelId) {
    if (levelId === activeLevel) return;
    setActiveLevel(levelId);
    resetChat();
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
      <div className="chat-header">
        <p className="chat-instructions">The AI model was told a secret word and instructed to never reveal it. Can you convince the model to reveal the word?</p>
        {messages.length > 0 && (
          <button className="clear-btn" onClick={resetChat} aria-label="Clear chat" title="Clear chat" disabled={streaming}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 11v6m4-6v6m5-11v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        )}
      </div>
      <LevelPills
        levels={levels}
        activeLevel={activeLevel}
        onSelect={handleLevelChange}
        disabled={streaming}
      />
      {messages.length > 0 && (
        <div className="message-thread" ref={scrollRef}>
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
      )}
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
          height: 100%;
          display: flex;
          flex-direction: column;
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius-xl);
          overflow: hidden;
          transition: border-color 0.3s, box-shadow 0.3s;
        }
        .chat-header {
          padding: var(--space-3) var(--space-5);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--space-3);
          position: relative;
        }
        .chat-instructions {
          font-size: var(--text-sm);
          color: var(--text-muted);
          line-height: 1.5;
          text-align: center;
        }
        .clear-btn {
          position: absolute;
          right: var(--space-5);
          top: 50%;
          transform: translateY(-50%);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: var(--radius-sm);
          color: var(--text-faint);
          transition: color 0.15s, background 0.15s;
        }
        .clear-btn svg {
          display: block;
        }
        .clear-btn:hover:not(:disabled) { color: var(--error); background: color-mix(in oklch, var(--error) 10%, transparent); }
        .clear-btn:disabled { opacity: 0.4; cursor: not-allowed; }
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
        @media (max-width: 768px) {
          .chatbox {
            border-radius: var(--radius-lg);
          }
        }
        @media (max-width: 480px) {
          .chatbox {
            border-radius: var(--radius-md);
          }
          .chat-header {
            padding-right: calc(var(--space-5) + 32px);
            padding-left: calc(var(--space-5) + 32px);
          }
          .clear-btn {
            right: var(--space-4);
          }
        }
      `}</style>
    </div>
  );
}
