import { useQuery } from '@tanstack/react-query';

import type { UploadLimitsResponse } from '@/shared/types';
import { fetchSettings } from '../api/settings';
import { settingsKeys } from '../api/queryKeys';

/**
 * The largest file each upload takes, as the backend is configured; null until they
 * load, or if they couldn't be (the backend still checks every upload).
 */
export function useUploadLimits(): UploadLimitsResponse | null {
  const { data } = useQuery({
    queryKey: settingsKeys.all,
    queryFn: ({ signal }) => fetchSettings(signal),
    // Configuration: it only changes with a redeploy.
    staleTime: Infinity,
  });
  return data?.uploads ?? null;
}
