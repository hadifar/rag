import type { SubmitEvent } from 'react';

import { KnowledgeBaseSection } from '../components/settings/KnowledgeBaseSection';
import { useAuth } from '../hooks/useAuth';
import { useSettings } from '../hooks/useSettings';

const inputCls =
  'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-normal text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition';
const labelCls = 'flex flex-col gap-1.5 text-sm font-medium text-slate-700';

export function SettingsPage() {
  const { form, status, saved, update, save } = useSettings();
  const { user } = useAuth();

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    save();
  };

  if (status === 'loading') {
    return <p className="p-8 text-sm text-slate-500">Loading settings…</p>;
  }

  return (
    <div>
      <form className="flex max-w-xl flex-col gap-4 p-8" onSubmit={handleSubmit}>
        <h1 className="mb-2 text-xl font-semibold text-slate-900">Settings</h1>

        {status === 'error' && (
          <p className="text-sm text-amber-600">
            Couldn't load defaults from the server — showing blank fields.
          </p>
        )}

        <label className={labelCls}>
          Model
          <input className={inputCls} value={form.model} onChange={(e) => update('model', e.target.value)} />
        </label>

        <label className={labelCls}>
          Temperature
          <input
            className={inputCls}
            type="number" min={0} max={2} step={0.1} value={form.temperature}
            onChange={(e) => update('temperature', Number(e.target.value))}
          />
        </label>

        <label className={labelCls}>
          Top K (retrieved chunks)
          <input
            className={inputCls}
            type="number" min={1} step={1} value={form.top_k}
            onChange={(e) => update('top_k', Number(e.target.value))}
          />
        </label>



        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Save
          </button>
          {saved && <span className="text-sm text-green-600">Saved</span>}
        </div>
      </form>

      {user?.is_admin && <KnowledgeBaseSection />}
    </div>
  );
}
