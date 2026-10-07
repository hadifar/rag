/**
 * The file as a data URL, to show as an image. A data URL, not an object URL: it needs
 * no revoking, and the page's CSP already allows `data:` images.
 */
export function readAsDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error('could not read the file'));
    reader.readAsDataURL(blob);
  });
}
