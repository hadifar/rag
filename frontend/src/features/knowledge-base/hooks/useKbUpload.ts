import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/shared/api/client';
import type { IngestionRunResponse } from '@/shared/types';
import {
  fetchIngestionRun,
  fetchLatestIngestionRun,
  uploadKnowledgeBase,
} from '../api/ingestions';
import { ingestionKeys } from '../api/queryKeys';
import { describeRun, runTime } from '../model/ingestions';
import type { UploadPhase } from '../types';

const POLL_INTERVAL_MS = 2000;
// Consecutive failed status checks (network blips) tolerated before giving up.
const MAX_POLL_FAILURES = 5;
const LOST_CONTACT = 'Lost contact with the server; check back here in a while.';

/**
 * Uploading a knowledge-base zip and following its ingestion run until it ends. The
 * run keeps going on the server even if the page closes; on load this picks a still
 * running one back up.
 */
export function useKbUpload() {
  const queryClient = useQueryClient();

  // The most recent run: what the page shows, and the run it follows while it's running.
  // On failure only the "last updated" line is missing; uploading still works.
  const { data: latest = null } = useQuery({
    queryKey: ingestionKeys.latest,
    queryFn: ({ signal }) => fetchLatestIngestionRun(signal),
  });
  const setLatest = useCallback(
    (run: IngestionRunResponse) => queryClient.setQueryData(ingestionKeys.latest, run),
    [queryClient]
  );
  const isRunning = latest?.status === 'running';

  // Each status check updates `latest`, so polling stops by itself once the run ends.
  // Its data also marks the run as followed from this page, to report how it ended.
  const poll = useQuery({
    queryKey: ingestionKeys.run(latest?.id),
    queryFn: async () => {
      const run = await fetchIngestionRun(latest!.id);
      setLatest(run);
      return run;
    },
    enabled: isRunning,
    refetchInterval: (query) => (query.state.status === 'error' ? false : POLL_INTERVAL_MS),
    retry: MAX_POLL_FAILURES - 1,
    retryDelay: POLL_INTERVAL_MS,
  });

  const uploading = useMutation({
    mutationFn: uploadKnowledgeBase,
    onSuccess: setLatest,
  });

  let phase: UploadPhase = 'idle';
  let error: string | null = null;
  if (uploading.isPending) {
    phase = 'uploading';
  } else if (uploading.isError) {
    phase = 'failed';
    error = uploading.error instanceof ApiError ? uploading.error.message : "Couldn't reach the server.";
  } else if (isRunning) {
    phase = poll.isError ? 'failed' : 'running';
    error = poll.isError ? LOST_CONTACT : null;
  } else if (latest && poll.data !== undefined) {
    phase = latest.status;
    error = latest.status === 'failed' ? (latest.error ?? 'The ingestion failed.') : null;
  }
  const busy = phase === 'uploading' || phase === 'running';

  const { mutate: upload, reset: resetUpload } = uploading;
  const runId = latest?.id;

  /** Clears a finished upload's result, e.g. when the dialog closes. */
  const dismiss = useCallback(() => {
    if (busy) return;
    resetUpload();
    void queryClient.resetQueries({ queryKey: ingestionKeys.run(runId) });
  }, [busy, resetUpload, queryClient, runId]);

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
