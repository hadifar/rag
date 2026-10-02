import { useEffect, useRef } from 'react';

/**
 * Loads once, when the component mounts. If it unmounts first, the request is aborted
 * and neither callback runs. The callbacks from the first render are the ones used,
 * so pass ones that don't depend on later renders (state setters are fine).
 */
export function useLoadOnMount<T>(
  load: (signal: AbortSignal) => Promise<T>,
  onLoad: (data: T) => void,
  onError?: () => void
) {
  const callbacks = useRef({ load, onLoad, onError });

  useEffect(() => {
    const { load, onLoad, onError } = callbacks.current;
    const controller = new AbortController();
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) onLoad(data);
      },
      () => {
        if (!controller.signal.aborted) onError?.();
      }
    );
    return () => controller.abort();
  }, []);
}
