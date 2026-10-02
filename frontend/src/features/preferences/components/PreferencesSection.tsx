import type { SubmitEvent } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

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
      <p className="m-0 text-sm text-slate-500">
        The assistant follows these in every conversation. You can also just tell it in a chat,
        e.g. "always answer in Dutch".
      </p>

      {status === 'loading' && <p className="m-0 text-sm text-slate-500">Loading preferences…</p>}
      {status === 'error' && (
        <p className="m-0 text-sm text-amber-600">Couldn't load your preferences.</p>
      )}
      {status === 'ready' && preferences.length === 0 && (
        <p className="m-0 text-sm text-slate-500">No preferences yet.</p>
      )}

      {preferences.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {preferences.map((preference) => (
            <li
              key={preference.id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800"
            >
              <span>{preference.text}</span>
              <button
                type="button"
                onClick={() => remove(preference.id)}
                aria-label={`Remove "${preference.text}"`}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form className="flex gap-2" onSubmit={handleSubmit}>
        <input
          className="flex-1 rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={draft}
          maxLength={MAX_PREFERENCE_LENGTH}
          placeholder="e.g. Keep answers short"
          aria-label="New preference"
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          disabled={!canAdd}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Add
        </button>
      </form>

      {error && <p className="m-0 text-sm text-red-600">{error}</p>}
    </section>
  );
}
