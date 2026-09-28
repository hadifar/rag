import type { Schemas } from '../types';

type IngestionRun = Schemas['IngestionRunResponse'];

/** One line on how a run went, e.g. "2 added, 1 removed (27 documents)". */
export function describeRun(run: IngestionRun): string {
  if (run.status === 'running') return 'Indexing…';
  if (run.status === 'failed') return run.error ?? 'Failed.';

  const added = run.added ?? 0;
  const updated = run.updated ?? 0;
  const changes = [
    [added, 'added'],
    [updated, 'updated'],
    [run.removed ?? 0, 'removed'],
  ]
    .filter(([count]) => count !== 0)
    .map(([count, label]) => `${count} ${label}`);
  const total = added + updated + (run.unchanged ?? 0);
  const documents = `${total} document${total === 1 ? '' : 's'}`;
  return changes.length ? `${changes.join(', ')} (${documents})` : `No changes (${documents})`;
}

/** When the run ended, or started if it's still going, in the viewer's locale. */
export function runTime(run: IngestionRun): string {
  return new Date(run.finished_at ?? run.started_at).toLocaleString();
}
