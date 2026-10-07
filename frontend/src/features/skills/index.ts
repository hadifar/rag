// The skills feature's public API: import it from '@/features/skills', never a file inside.
export { SkillsSection } from './components/SkillsSection';
export { useSkillList } from './hooks/useSkillList';
export { useSkillUpload, type SkillUpload } from './hooks/useSkillUpload';
export { SKILL_ACCEPT } from './model/skills';
