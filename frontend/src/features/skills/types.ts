import type { SkillResponse } from '@/shared/types';

/** A line on how a skill upload went. */
export type SkillNotice = { text: string; tone: 'success' | 'warning' };

/** A skill as the skills list shows it. */
export type SkillRow = SkillResponse & { filesLabel: string | null };
