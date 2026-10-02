import { useCallback } from 'react';

import { fetchKbSource } from '../api/retrieval';

// How long the opened tab gets to load the document before its blob URL is released.
const URL_LIFETIME_MS = 10_000;

/** Opens a knowledge-base document (e.g. one an answer cites) in a new tab. */
export function useOpenKbSource() {
  return useCallback((name: string) => {
    fetchKbSource(name)
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noreferrer');
        setTimeout(() => URL.revokeObjectURL(url), URL_LIFETIME_MS);
      })
      .catch(() => window.alert("Couldn't open that document. Please try again."));
  }, []);
}
