import { useCallback, useEffect, useRef, useState } from 'react';

/** How long the "copied" or "failed" state shows before the button resets. */
const RESET_MS = 2000;

export type CopyState = 'idle' | 'copied' | 'failed';

/** Copies `text` to the clipboard, and says how the last copy went for a short while. */
export function useCopyText(text: string) {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  const show = useCallback((next: CopyState) => {
    setState(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setState('idle'), RESET_MS);
  }, []);

  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(
      () => show('copied'),
      () => show('failed')
    );
  }, [text, show]);

  return { state, copy };
}
