const COOKIE_NAME = 'access_token';
const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export function setAuthCookie(token: string): void {
  const expiry = new Date(Date.now() + SEVEN_DAYS_MS);
  document.cookie = `${COOKIE_NAME}=${token}; path=/; samesite=strict; expires=${expiry.toUTCString()}`;
}

export function clearAuthCookie(): void {
  document.cookie = `${COOKIE_NAME}=; path=/; samesite=strict; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
}
