import { useState, type SubmitEvent, type KeyboardEvent } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';

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
    // isComposing: an IME candidate is still being picked (e.g. typing Japanese/Chinese/
    // Korean) — that Enter confirms the candidate, it doesn't mean "send".
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
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
        <Button type="submit" size="icon" aria-label="Send" disabled={!value.trim()}>
          <PaperAirplaneIcon className="size-4" />
        </Button>
      </div>
    </form>
  );
}
