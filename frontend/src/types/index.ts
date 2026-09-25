export * from './chat';

import type { components } from './api.generated';

export type Settings = components['schemas']['SettingsResponse'];
export type ChatRequest = components['schemas']['ChatRequest'];
