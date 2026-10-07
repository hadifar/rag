import type { components, paths } from './api.generated';

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
export type TodoItem = Schemas['TodoItem'];
export type TodosEvent = Schemas['TodosEvent'];
export type VerificationEvent = Schemas['VerificationEvent'];
export type SourceArtifactItem = Schemas['SourceArtifactItem'];
export type ArtifactsEvent = Schemas['ArtifactsEvent'];
export type ErrorEvent = Schemas['ErrorEvent'];
export type StreamEventResponse = Schemas['StreamEventResponse'];

// conversation.py
export type ConversationResponse = Schemas['ConversationResponse'];
export type ConversationPageResponse = Schemas['ConversationPageResponse'];
export type UserMessageResponse = Schemas['UserMessageResponse'];
export type AssistantMessageResponse = Schemas['AssistantMessageResponse'];
export type HistoryMessageResponse = Schemas['HistoryMessageResponse'];
export type MessageRequest = Schemas['MessageRequest'];
export type ChatMessageRequest = Schemas['ChatMessageRequest'];
export type AttachmentResponse = Schemas['AttachmentResponse'];
export type ConversationUpdateRequest = Schemas['ConversationUpdateRequest'];

// health.py
export type HealthResponse = Schemas['HealthResponse'];

// ingestion.py
export type IngestionRunResponse = Schemas['IngestionRunResponse'];

// skill.py
export type SkillResponse = Schemas['SkillResponse'];

// share.py
export type ShareResponse = Schemas['ShareResponse'];
export type SharedConversationResponse = Schemas['SharedConversationResponse'];

// setting.py
export type SettingsResponse = Schemas['SettingsResponse'];
export type UploadLimitsResponse = Schemas['UploadLimitsResponse'];

// Every route, with its parameters, body and responses: what the typed `api` client checks
// each call against (shared/api/client.ts).
export type ApiPaths = paths;
