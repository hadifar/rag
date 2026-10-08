import type { Effort, ModelName, RunSettings } from '../types';

/** The models a conversation can run on; each is shown by its id. */
export const MODELS: ModelName[] = ['gpt-6-luna', 'gpt-6-astra', 'gpt-6-sol'];

export const EFFORTS: { value: Effort; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

// Keep in sync with DEFAULT_MODEL and DEFAULT_EFFORT in rag/domain/models/agent/agent.py.
export const DEFAULT_RUN_SETTINGS: RunSettings = { model: 'gpt-6-luna', effort: 'low' };

export function effortLabel(effort: Effort): string {
  return EFFORTS.find((e) => e.value === effort)?.label ?? effort;
}

/** The fields of `wanted` that `current` doesn't have yet; null if none. */
export function settingsToChange(current: RunSettings, wanted: RunSettings): Partial<RunSettings> | null {
  const change: Partial<RunSettings> = {};
  if (current.model !== wanted.model) change.model = wanted.model;
  if (current.effort !== wanted.effort) change.effort = wanted.effort;
  return Object.keys(change).length > 0 ? change : null;
}
