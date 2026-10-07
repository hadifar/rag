import { useCallback, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { ignoreNotFound } from '@/shared/api/errors';
import type { SkillResponse } from '@/shared/types';
import { skillKeys } from '../api/queryKeys';
import { deleteSkill } from '../api/skills';
import { useSkillList } from './useSkillList';

const DELETE_FAILED = "Couldn't delete the skill. Please try again.";

/** The user's skills, and a delete that waits for the user to confirm it. */
export function useSkills() {
  const queryClient = useQueryClient();
  const { skills, status } = useSkillList();
  const [pending, setPending] = useState<SkillResponse | null>(null);

  const { mutate, reset, isPending, isError } = useMutation({
    // Already gone is success too; without this, a retry would 404 forever.
    mutationFn: (id: string) => ignoreNotFound(deleteSkill(id)),
    onSuccess: (_, id) => {
      queryClient.setQueryData<SkillResponse[]>(skillKeys.list, (skills) =>
        skills?.filter((s) => s.id !== id)
      );
      setPending(null);
    },
  });

  const requestDelete = useCallback(
    (skill: SkillResponse) => {
      reset();
      setPending(skill);
    },
    [reset]
  );

  const cancel = useCallback(() => {
    // Closing mid-request would hide whether the delete worked.
    if (!isPending) setPending(null);
  }, [isPending]);

  const confirm = useCallback(() => {
    if (pending && !isPending) mutate(pending.id);
  }, [pending, isPending, mutate]);

  return {
    skills,
    status,
    pending,
    isDeleting: isPending,
    deleteError: isError ? DELETE_FAILED : null,
    requestDelete,
    confirm,
    cancel,
  };
}
