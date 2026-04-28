import { authHeaders } from './auth.js';

const BASE = '/api';

export async function login(password) {
    const res = await fetch(`${BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Login failed');
    }
    return res.json();
}

export async function fetchLevels() {
    const res = await fetch(`${BASE}/levels`);
    if (!res.ok) throw new Error('Failed to fetch levels');
    return res.json();
}

export async function fetchHealth() {
    const res = await fetch(`${BASE}/health`);
    if (!res.ok) return { online: false };
    return res.json();
}

export async function fetchStats() {
    const res = await fetch(`${BASE}/stats`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

/**
 * Stream a chat message via SSE.
 * @param {string} level
 * @param {Array} messages - previous messages array
 * @param {string} prompt - new user message
 * @param {function} onToken - called for each token string
 * @returns {Promise<{success: boolean}>}
 */
export async function streamChat(level, messages, prompt, onToken) {
    const res = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders(),
        },
        body: JSON.stringify({ level, messages, prompt }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Chat failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let success = false;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;
            try {
                const event = JSON.parse(raw);
                if (event.delta !== undefined) {
                    onToken(event.delta);
                } else if (event.done) {
                    success = event.success;
                } else if (event.error) {
                    throw new Error(event.error);
                }
            } catch (e) {
                if (e.message && e.message !== 'Unexpected end of JSON input') throw e;
            }
        }
    }

    return { success };
}
