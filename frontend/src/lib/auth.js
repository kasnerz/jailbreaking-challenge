// Persisted to sessionStorage to survive page navigation, but cleared when tab is closed
export function setToken(token) {
    sessionStorage.setItem('jwt_token', token);
}

export function getToken() {
    return sessionStorage.getItem('jwt_token');
}

export function clearToken() {
    sessionStorage.removeItem('jwt_token');
}

export function isAuthenticated() {
    return getToken() !== null;
}

export function authHeaders() {
    const token = getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
}
