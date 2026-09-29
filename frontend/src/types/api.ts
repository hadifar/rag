import type { components } from './api.generated';

// All backend request/response schemas, keyed by name (e.g. Schemas['MessageRequest']).
export type Schemas = components['schemas'];

export type Conversation = Schemas['ConversationResponse'];
