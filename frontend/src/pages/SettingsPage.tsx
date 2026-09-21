import { type SubmitEvent, useState } from 'react';
import type { Settings } from '../types';

const inputCls =
  'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-normal text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition';
const labelCls = 'flex flex-col gap-1.5 text-sm font-medium text-slate-700';

const DEFAULTS: Settings = { model: '', temperature: 0, top_k: 4, system_prompt: '' };

export default function SettingsPage() {
  const [form, setForm] = useState<Settings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  // TODO: load and persist via the settings API once the client exists.
  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <form className="flex max-w-xl flex-col gap-4 p-8" onSubmit={handleSubmit}>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Settings</h1>

      <label className={labelCls}>
        Model
        <input className={inputCls} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
      </label>

      <label className={labelCls}>
        Temperature
        <input
          className={inputCls}
          type="number" min={0} max={2} step={0.1} value={form.temperature}
          onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })}
        />
      </label>

      <label className={labelCls}>
        Top K (retrieved chunks)
        <input
          className={inputCls}
          type="number" min={1} step={1} value={form.top_k}
          onChange={(e) => setForm({ ...form, top_k: Number(e.target.value) })}
        />
      </label>

      <label className={labelCls}>
        System prompt
        <textarea
          className={inputCls}
          rows={6} value={form.system_prompt}
          onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
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
  );
}
