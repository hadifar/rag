import { useQuery } from '@tanstack/react-query';

import { loadStatus } from '@/shared/api/queryClient';
import type { SkillResponse } from '@/shared/types';
import { skillKeys } from '../api/queryKeys';
import { fetchSkills } from '../api/skills';

const NO_SKILLS: SkillResponse[] = [];

/** The user's skills, by name; none while they load. */
export function useSkillList() {
  const query = useQuery({
    queryKey: skillKeys.list,
    queryFn: ({ signal }) => fetchSkills(signal),
  });
  return { skills: query.data ?? NO_SKILLS, status: loadStatus(query) };
}
