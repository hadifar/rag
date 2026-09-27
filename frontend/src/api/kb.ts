import { request } from './client';

export async function openKbSource(name: string): Promise<void> {
  const blob = await (await request(`kb/${encodeURIComponent(name)}`)).blob();
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
