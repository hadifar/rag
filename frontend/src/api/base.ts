const API_BASE = 'api';

export function apiUrl(path: string): string {
  return `${API_BASE}/${path}`;
}

export function jsonPost(body: unknown) {
  return {
    method: 'POST' as const,
    headers: { 'Content-Type': 'application/json' } as Record<string, string>,
    body: JSON.stringify(body),
  };
}
