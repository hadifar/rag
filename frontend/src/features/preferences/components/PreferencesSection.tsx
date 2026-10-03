import type { SubmitEvent } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';
import { IconButton } from '@/shared/ui/IconButton';
import { Input } from '@/shared/ui/Input';
import { StatusLine } from '@/shared/ui/StatusLine';
import { usePreferences } from '../hooks/usePreferences';
import { MAX_PREFERENCE_LENGTH } from '../model/preferences';

/** The user's answer preferences: what the assistant follows in every conversation. */
export function PreferencesSection() {
  const { preferences, status, draft, setDraft, canAdd, error, add, remove } = usePreferences();

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    add();
  };

  return (
    <section className="flex max-w-xl flex-col gap-3 border-t border-slate-200 p-8">
      <h2 className="m-0 text-base font-semibold text-slate-900">Answer preferences</h2>
      <StatusLine>
        The assistant follows these in every conversation. You can also just tell it in a chat,
        e.g. "always answer in Dutch".
      </StatusLine>

      {status === 'loading' && <StatusLine>Loading preferences…</StatusLine>}
      {status === 'error' && <StatusLine tone="warning">Couldn't load your preferences.</StatusLine>}
      {status === 'ready' && preferences.length === 0 && <StatusLine>No preferences yet.</StatusLine>}

      {preferences.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {preferences.map((preference) => (
            <li
              key={preference.id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800"
            >
              <span>{preference.text}</span>
              <IconButton label={`Remove "${preference.text}"`} onClick={() => remove(preference.id)}>
                <XMarkIcon className="size-4" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}

      <form className="flex gap-2" onSubmit={handleSubmit}>
        <Input
          className="flex-1"
          value={draft}
          maxLength={MAX_PREFERENCE_LENGTH}
          placeholder="e.g. Keep answers short"
          aria-label="New preference"
          onChange={(e) => setDraft(e.target.value)}
        />
        <Button type="submit" disabled={!canAdd}>
          Add
        </Button>
      </form>

      {error && <StatusLine tone="error">{error}</StatusLine>}
    </section>
  );
}
