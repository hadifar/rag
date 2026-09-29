import type { components } from './api.generated';

// One type per backend schema, named as in rag/api/schema/ — import these, never
// `components` directly, so every backend shape used here is listed in one place.
type Schemas = components['schemas'];

// auth.py
export type LoginRequest = Schemas['LoginRequest'];
export type TokenResponse = Schemas['TokenResponse'];
export type UserResponse = Schemas['UserResponse'];

// conversations.py
export type ConversationResponse = Schemas['ConversationResponse'];
export type ConversationPageResponse = Schemas['ConversationPageResponse'];
export type HistoryMessageResponse = Schemas['HistoryMessageResponse'];
export type MessageRequest = Schemas['MessageRequest'];
export type TextEvent = Schemas['TextEvent'];
export type ToolEvent = Schemas['ToolEvent'];
export type SourcesEvent = Schemas['SourcesEvent'];
export type StreamEventResponse = Schemas['StreamEventResponse'];

// health.py
export type HealthResponse = Schemas['HealthResponse'];

// ingestions.py
export type IngestionRunResponse = Schemas['IngestionRunResponse'];

// settings.py
export type SettingsResponse = Schemas['SettingsResponse'];
