import { useAuth } from '@/features/auth';
import { KnowledgeBaseSection } from '@/features/knowledge-base';
import { SkillsSection } from '@/features/skills';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <h1 className="m-0 px-8 pt-8 pb-6 text-xl font-semibold text-slate-900">Settings</h1>

      <SkillsSection />

      {user?.is_admin && <KnowledgeBaseSection />}
    </div>
  );
}
