const KB = 1024;
const MB = 1024 * KB;

/** A size in bytes as the user reads it, e.g. "512 KB" or "20 MB". */
export function sizeLabel(bytes: number): string {
  return bytes >= MB ? `${+(bytes / MB).toFixed(1)} MB` : `${+(bytes / KB).toFixed(1)} KB`;
}
