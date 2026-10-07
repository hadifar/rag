import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { errorDetail } from '@/shared/api/errors';
import type { SkillResponse } from '@/shared/types';
import { skillKeys } from '../api/queryKeys';
import { uploadSkill } from '../api/skills';
import { UPLOAD_FAILED, savedNotice, skillUploadProblem, withSkill } from '../model/skills';
import type { SkillNotice } from '../types';

const NOTICE_MS = 5000;

export type SkillUpload = {
  upload: (file: File) => void;
  uploading: boolean;
  /** How the last upload went, for a few seconds; null otherwise. */
  notice: SkillNotice | null;
};

/**
 * Uploads a SKILL.md file, or a .zip or .skill archive of one, to the user's skills, and says
 * how it went. A file of the wrong type or over the size limit is turned down without sending it.
 */
export function useSkillUpload(): SkillUpload {
  const queryClient = useQueryClient();
  const [refused, setRefused] = useState<string | null>(null);
  const { mutate, reset, isPending, data, error } = useMutation({
    mutationFn: (file: File) => uploadSkill(file),
    onSuccess: (skill) => {
      queryClient.setQueryData<SkillResponse[]>(skillKeys.list, (skills) =>
        skills ? withSkill(skills, skill) : skills
      );
    },
  });

  const notice: SkillNotice | null = refused
    ? { text: refused, tone: 'warning' }
    : data
      ? { text: savedNotice(data), tone: 'success' }
      : error
        ? { text: errorDetail(error) ?? UPLOAD_FAILED, tone: 'warning' }
        : null;

  // Hide the notice again after a moment.
  useEffect(() => {
    if (!refused && !data && !error) return;
    const timer = setTimeout(() => {
      setRefused(null);
      reset();
    }, NOTICE_MS);
    return () => clearTimeout(timer);
  }, [refused, data, error, reset]);

  const upload = useCallback(
    (file: File) => {
      const problem = skillUploadProblem(file);
      reset();
      setRefused(problem);
      if (!problem) mutate(file);
    },
    [mutate, reset]
  );

  return { upload, uploading: isPending, notice };
}
