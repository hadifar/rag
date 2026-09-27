import { useState, type SubmitEvent, type KeyboardEvent } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/outline';

export function Composer({ onSend }: { onSend: (text: string) => void }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue('');
  };

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="shrink-0 border-t border-slate-200 p-4">
      <div className="mx-auto flex max-w-[720px] items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Type a message..."
          className="h-11 max-h-40 flex-1 resize-none border-none bg-transparent p-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:ring-0"
        />
        <button
          type="submit"
          disabled={!value.trim()}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:opacity-40"
        >
          <PaperAirplaneIcon className="size-4" />
        </button>
      </div>
    </form>
  );
}
