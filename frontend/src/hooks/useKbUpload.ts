import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../api/client';
import {
  fetchIngestionRun,
  fetchLatestIngestionRun,
  uploadKnowledgeBase,
} from '../api/ingestions';
import type { IngestionRunResponse } from '../types';
import { describeRun, runTime } from '../utils/ingestions';

/** `failed` covers both a rejected upload and a run that failed; `error` says which. */
export type UploadPhase = 'idle' | 'uploading' | 'running' | 'succeeded' | 'failed';

export const POLL_INTERVAL_MS = 2000;
// Consecutive failed status checks (network blips) tolerated before giving up.
const MAX_POLL_FAILURES = 5;

/**
 * Uploading a knowledge-base zip and following its ingestion run until it ends. The
 * run keeps going on the server even if the page closes; on load this picks a still
 * running one back up.
 */
export function useKbUpload() {
  const [latest, setLatest] = useState<IngestionRunResponse | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchLatestIngestionRun()
      .then((run) => {
        if (cancelled) return;
        setLatest(run);
        if (run?.status === 'running') {
          setRunId(run.id);
          setPhase('running');
        }
      })
      // Only the "last updated" line is missing then; uploading still works.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (phase !== 'running' || runId === null) return;
    let cancelled = false;
    let failures = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const run = await fetchIngestionRun(runId);
        if (cancelled) return;
        failures = 0;
        setLatest(run);
        if (run.status === 'running') {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
          return;
        }
        setError(run.status === 'failed' ? (run.error ?? 'The ingestion failed.') : null);
        setPhase(run.status);
      } catch {
        if (cancelled) return;
        failures += 1;
        if (failures < MAX_POLL_FAILURES) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
          return;
        }
        setError('Lost contact with the server; check back here in a while.');
        setPhase('failed');
      }
    };

    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [phase, runId]);

  const upload = useCallback(async (file: File) => {
    setError(null);
    setPhase('uploading');
    try {
      const run = await uploadKnowledgeBase(file);
      setLatest(run);
      setRunId(run.id);
      setPhase('running');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the server.");
      setPhase('failed');
    }
  }, []);

  const busy = phase === 'uploading' || phase === 'running';

  /** Clears a finished upload's result, e.g. when the dialog closes. */
  const dismiss = useCallback(() => {
    if (busy) return;
    setError(null);
    setPhase('idle');
  }, [busy]);

  return {
    phase,
    error,
    busy,
    // The latest run, ready to display; null until one exists.
    summary: latest ? describeRun(latest) : null,
    lastRunAt: latest ? runTime(latest) : null,
    lastRunStatus: latest?.status ?? null,
    upload,
    dismiss,
  };
}
