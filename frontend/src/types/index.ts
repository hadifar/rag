export * from './chat';

export type Settings = {
  model: string;
  temperature: number;
  top_k: number;
  system_prompt: string;
};
