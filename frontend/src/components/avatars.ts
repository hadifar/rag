function initialsAvatar(letter: string, background: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" rx="20" fill="${background}"/><text x="20" y="26" font-family="system-ui,sans-serif" font-size="16" fill="#fff" text-anchor="middle">${letter}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export const USER = { avatar: initialsAvatar('U', '#5b8def'), avatarAlt: 'You' };
export const ASSISTANT = { avatar: initialsAvatar('A', '#7c5cff'), avatarAlt: 'Assistant' };
