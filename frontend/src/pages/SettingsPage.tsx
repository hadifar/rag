import { useAuth } from '@/features/auth';
import { KnowledgeBaseSection } from '@/features/knowledge-base';
import { PreferencesSection } from '@/features/preferences';
import { SettingsForm } from '@/features/settings';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <SettingsForm />

      <PreferencesSection />

      {user?.is_admin && <KnowledgeBaseSection />}
    </div>
  );
}
