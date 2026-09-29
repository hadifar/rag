/** `failed` covers both a rejected upload and a run that failed; `error` says which. */
export type UploadPhase = 'idle' | 'uploading' | 'running' | 'succeeded' | 'failed';
