import { apiUrl } from './base';

export function kbSourceUrl(name: string): string {
  return apiUrl(`kb/${name}`);
}
