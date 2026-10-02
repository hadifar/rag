/**
 * Collects items and hands them over at most once per animation frame. A streamed answer
 * sends an event per token; applying them a frame at a time keeps a long answer from
 * re-rendering (and re-parsing its markdown, and re-scrolling) hundreds of times.
 */
export function frameBatcher<T>(flush: (items: T[]) => void) {
  let items: T[] = [];
  let handle: number | null = null;

  const flushNow = () => {
    if (handle !== null) cancelAnimationFrame(handle);
    handle = null;
    if (items.length === 0) return;
    const batch = items;
    items = [];
    flush(batch);
  };

  return {
    push(item: T) {
      items.push(item);
      handle ??= requestAnimationFrame(flushNow);
    },
    /** Hands over what's collected right away, e.g. before the stream's end is shown. */
    flushNow,
    /** Drops what's collected, e.g. once the stream is aborted. */
    cancel() {
      if (handle !== null) cancelAnimationFrame(handle);
      handle = null;
      items = [];
    },
  };
}
