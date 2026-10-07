import { useAuth } from '@/features/auth';
import { KnowledgeBaseSection } from '@/features/knowledge-base';
import { SettingsForm } from '@/features/settings';
import { SkillsSection } from '@/features/skills';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <SettingsForm />

      <SkillsSection />

      {user?.is_admin && <KnowledgeBaseSection />}
    </div>
  );
}
