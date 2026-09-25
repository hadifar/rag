export * from './chat';

import type { components } from './api.generated';

// All backend request/response schemas, keyed by name (e.g. Schemas['ChatRequest']).
export type Schemas = components['schemas'];
