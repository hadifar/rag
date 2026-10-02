import { useCallback } from 'react';

import { openKbSource } from '../api/retrieval';

/** Opens a knowledge-base document (e.g. one an answer cites) in a new tab. */
export function useOpenKbSource() {
  return useCallback((name: string) => {
    openKbSource(name).catch(() => window.alert("Couldn't open that document. Please try again."));
  }, []);
}
