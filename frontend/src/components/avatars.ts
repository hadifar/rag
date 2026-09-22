const USER_ICON =
  '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7"/>';

const ROBOT_ICON =
  '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4"/>' +
  '<circle cx="12" cy="3" r="1.2" fill="#fff" stroke="none"/>' +
  '<circle cx="9" cy="14" r="1.2" fill="#fff" stroke="none"/>' +
  '<circle cx="15" cy="14" r="1.2" fill="#fff" stroke="none"/>' +
  '<path d="M9 18h6"/>';

function iconAvatar(iconPaths: string, background: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" rx="20" fill="${background}"/><svg x="9" y="9" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${iconPaths}</svg></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export const USER = { avatar: iconAvatar(USER_ICON, '#5b8def'), avatarAlt: 'You' };
export const ASSISTANT = { avatar: iconAvatar(ROBOT_ICON, '#7c5cff'), avatarAlt: 'Assistant' };
