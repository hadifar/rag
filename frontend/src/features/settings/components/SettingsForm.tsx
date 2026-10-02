import type { SubmitEvent } from 'react';

import { Button } from '@/shared/ui/Button';
import { TextField } from '@/shared/ui/Input';
import { StatusLine } from '@/shared/ui/StatusLine';
import { useSettings } from '../hooks/useSettings';

/** The model settings: loaded from the server, edited locally, and saved. */
export function SettingsForm() {
  const { form, status, saved, update, save } = useSettings();

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    save();
  };

  if (status === 'loading') {
    return <StatusLine className="p-8">Loading settings…</StatusLine>;
  }

  return (
    <form className="flex max-w-xl flex-col gap-4 p-8" onSubmit={handleSubmit}>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Settings</h1>

      {status === 'error' && (
        <StatusLine tone="warning">
          Couldn't load defaults from the server — showing blank fields.
        </StatusLine>
      )}

      <TextField label="Model" value={form.model} onChange={(e) => update('model', e.target.value)} />
      <TextField
        label="Temperature"
        type="number" min={0} max={2} step={0.1} value={form.temperature}
        onChange={(e) => update('temperature', Number(e.target.value))}
      />
      <TextField
        label="Top K (retrieved chunks)"
        type="number" min={1} step={1} value={form.top_k}
        onChange={(e) => update('top_k', Number(e.target.value))}
      />

      <div className="flex items-center gap-3">
        <Button type="submit">Save</Button>
        {saved && <StatusLine tone="success">Saved</StatusLine>}
      </div>
    </form>
  );
}
