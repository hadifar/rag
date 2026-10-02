import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * `ui` with its own empty cache, so no test sees another's data. No retries: a failing
 * route shows its error at once instead of after the app's backoff.
 */
export function withQueryClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}
