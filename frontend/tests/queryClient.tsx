import { StrictMode, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * `ui` with its own empty cache, so no test sees another's data, in StrictMode as in
 * main.tsx (so an effect that can't run twice fails here too). No retries: a failing
 * route shows its error at once instead of after the app's backoff.
 */
export function withQueryClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <StrictMode>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </StrictMode>
  );
}
