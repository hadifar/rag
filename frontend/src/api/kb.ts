import { apiUrl, authFetch } from './client';

export async function openKbSource(name: string): Promise<void> {
  const res = await authFetch(apiUrl(`kb/${name}`));
  if (!res.ok) {
    throw new Error(`failed to load source: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noreferrer');
  // Revoke once the new tab has had a chance to load it.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
