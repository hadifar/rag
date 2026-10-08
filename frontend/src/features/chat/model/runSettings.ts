import type { Effort, ModelName, RunSettings } from '../types';

/** The models the user's turns can run on; each is shown by its id. */
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
