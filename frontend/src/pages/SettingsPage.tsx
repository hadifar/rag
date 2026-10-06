import { useAuth } from '@/features/auth';
import { KnowledgeBaseSection } from '@/features/knowledge-base';
import { SettingsForm } from '@/features/settings';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <SettingsForm />

      {user?.is_admin && <KnowledgeBaseSection />}
    </div>
  );
}
