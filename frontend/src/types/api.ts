import type { components } from './api.generated';

// One type per backend schema, named as in rag/api/schema/ — import these, never
// `components` directly, so every backend shape used here is listed in one place.
type Schemas = components['schemas'];

// auth.py
export type LoginRequest = Schemas['LoginRequest'];
export type TokenResponse = Schemas['TokenResponse'];
export type UserResponse = Schemas['UserResponse'];

// agent.py
export type TextEvent = Schemas['TextEvent'];
export type ReasoningEvent = Schemas['ReasoningEvent'];
export type ToolEvent = Schemas['ToolEvent'];
export type ReferencesEvent = Schemas['ReferencesEvent'];
export type StreamEventResponse = Schemas['StreamEventResponse'];

// conversation.py
export type ConversationResponse = Schemas['ConversationResponse'];
export type ConversationPageResponse = Schemas['ConversationPageResponse'];
export type HistoryMessageResponse = Schemas['HistoryMessageResponse'];
export type MessageRequest = Schemas['MessageRequest'];

// health.py
export type HealthResponse = Schemas['HealthResponse'];

// ingestion.py
export type IngestionRunResponse = Schemas['IngestionRunResponse'];

// setting.py
export type SettingsResponse = Schemas['SettingsResponse'];
export type PreferenceRequest = Schemas['PreferenceRequest'];
export type PreferenceResponse = Schemas['PreferenceResponse'];
