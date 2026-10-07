import { useCallback, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { errorDetail } from '@/shared/api/errors';
import type { SkillResponse } from '@/shared/types';
import { skillKeys } from '../api/queryKeys';
import { uploadSkill } from '../api/skills';
import { UPLOAD_FAILED, savedNotice, withSkill } from '../model/skills';
import type { SkillNotice } from '../types';

const NOTICE_MS = 5000;

export type SkillUpload = {
  upload: (file: File) => void;
  uploading: boolean;
  /** How the last upload went, for a few seconds; null otherwise. */
  notice: SkillNotice | null;
};

/** Uploads a SKILL.md file to the user's skills, and says how it went. */
export function useSkillUpload(): SkillUpload {
  const queryClient = useQueryClient();
  const { mutate, reset, isPending, data, error } = useMutation({
    mutationFn: (file: File) => uploadSkill(file),
    onSuccess: (skill) => {
      queryClient.setQueryData<SkillResponse[]>(skillKeys.list, (skills) =>
        skills ? withSkill(skills, skill) : skills
      );
    },
  });

  const notice: SkillNotice | null = data
    ? { text: savedNotice(data), tone: 'success' }
    : error
      ? { text: errorDetail(error) ?? UPLOAD_FAILED, tone: 'warning' }
      : null;

  // Hide the notice again after a moment.
  useEffect(() => {
    if (!data && !error) return;
    const timer = setTimeout(reset, NOTICE_MS);
    return () => clearTimeout(timer);
  }, [data, error, reset]);

  const upload = useCallback((file: File) => mutate(file), [mutate]);

  return { upload, uploading: isPending, notice };
}
