import {
  useCallback,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type KeyboardEvent,
  type SubmitEvent,
} from 'react';
import {
  LanguageIcon,
  PaperAirplaneIcon,
  PaperClipIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';
import { Dropdown, DropdownItem, DropdownOption } from '@/shared/ui/Dropdown';
import { ATTACHMENT_ACCEPT } from '../model/attachments';
import { EFFORTS, MODELS, effortLabel } from '../model/runSettings';
import { useSkillCommand } from '../hooks/useSkillCommand';
import type { AttachmentDraft, Effort, ModelName, SkillOption } from '../types';
import { DraftAttachments } from './AttachmentChips';
import { RunPicker } from './RunPicker';
import { SkillSuggestions } from './SkillSuggestions';

/** The files picked for the next message, from `useChat`. */
export type ComposerAttachments = {
  drafts: AttachmentDraft[];
  notice: string | null;
  uploading: boolean;
  hasReady: boolean;
  onAttach: (files: File[]) => void;
  onRemove: (key: string) => void;
};

/** The user's skills: invoked with "/<name>", and uploaded from the + menu. */
export type ComposerSkills = {
  /** Suggested while a "/" command is typed. */
  available: SkillOption[];
  /** What the skill picker offers. */
  accept: string;
  onUpload: (file: File) => void;
  uploading: boolean;
  /** How the last upload went, for a few seconds. */
  notice: { text: string; tone: 'success' | 'warning' } | null;
};

/** The model and effort the conversation's answers run on, from `useChat`. */
export type ComposerRun = {
  model: ModelName;
  effort: Effort;
  onModel: (model: ModelName) => void;
  onEffort: (effort: Effort) => void;
};

type ComposerProps = {
  onSend: (text: string) => void;
  /** Left out, the composer takes text only. */
  attachments?: ComposerAttachments;
  /** Left out, the + menu offers no skills. */
  skills?: ComposerSkills;
  /** Left out, no model or effort is shown. */
  run?: ComposerRun;
};

const NO_SKILLS: SkillOption[] = [];

const noticeTones = {
  success: 'text-success-600',
  warning: 'text-warning-700',
};

export function Composer({ onSend, attachments, skills, run }: ComposerProps) {
  const [value, setValue] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const closeMenu = useCallback(() => setIsMenuOpen(false), []);
  const menuButton = useRef<HTMLButtonElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const skillInput = useRef<HTMLInputElement>(null);
  const command = useSkillCommand(value, skills?.available ?? NO_SKILLS);
  const suggesting = command.suggestions.length > 0;
  const suggestionsId = useId();
  const optionId = (index: number) => `${suggestionsId}-${index}`;
  // A message needs text or a file, and waits for its files to finish uploading.
  const canSend = !attachments?.uploading && (value.trim() !== '' || !!attachments?.hasReady);

  const submit = () => {
    if (!canSend) return;
    onSend(value.trim());
    setValue('');
  };

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    submit();
  };

  // While skills are suggested, the arrows, Enter, Tab and Escape work the list.
  const handleSuggestionKey = (e: KeyboardEvent<HTMLTextAreaElement>): boolean => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') command.move(e.key === 'ArrowDown' ? 1 : -1);
    else if ((e.key === 'Enter' && !e.shiftKey) || e.key === 'Tab') setValue(command.pick());
    else if (e.key === 'Escape') command.dismiss();
    else return false;
    e.preventDefault();
    return true;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // isComposing: an IME candidate is still being picked (e.g. typing Japanese/Chinese/
    // Korean) — that Enter confirms the candidate, it doesn't mean "send".
    if (e.nativeEvent.isComposing) return;
    if (suggesting && handleSuggestionKey(e)) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handlePick = (e: ChangeEvent<HTMLInputElement>) => {
    attachments?.onAttach(Array.from(e.target.files ?? []));
    // Picking the same file again still fires a change.
    e.target.value = '';
  };

  const handlePickSkill = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) skills?.onUpload(file);
    e.target.value = '';
  };

  // A pasted file (e.g. a screenshot) is attached; pasted text is typed as usual.
  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(e.clipboardData.files);
    if (!attachments || files.length === 0) return;
    e.preventDefault();
    attachments.onAttach(files);
  };

  const handleDragOver = (e: DragEvent<HTMLFormElement>) => {
    if (attachments && e.dataTransfer.types.includes('Files')) e.preventDefault();
  };

  const handleDrop = (e: DragEvent<HTMLFormElement>) => {
    const files = Array.from(e.dataTransfer.files);
    if (!attachments || files.length === 0) return;
    e.preventDefault();
    attachments.onAttach(files);
  };

  return (
    <form
      onSubmit={handleSubmit}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="shrink-0 border-slate-200 p-4"
    >
      <div className="relative mx-auto max-w-[720px] rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        {suggesting && (
          <SkillSuggestions
            id={suggestionsId}
            optionId={optionId}
            suggestions={command.suggestions}
            activeIndex={command.activeIndex}
            onPick={(index) => setValue(command.pick(index))}
          />
        )}
        {attachments && attachments.drafts.length > 0 && (
          <DraftAttachments drafts={attachments.drafts} onRemove={attachments.onRemove} />
        )}
        {attachments?.notice && (
          <p role="status" className="m-0 px-2 pb-2 text-xs text-warning-700">
            {attachments.notice}
          </p>
        )}
        {skills?.notice && (
          <p role="status" className={`m-0 px-2 pb-2 text-xs ${noticeTones[skills.notice.tone]}`}>
            {skills.notice.text}
          </p>
        )}
        <div className="flex items-end gap-2">
          {(attachments || skills) && (
            <>
              <Button
                ref={menuButton}
                variant="ghost"
                size="icon"
                aria-label="Add files or skills"
                aria-haspopup="menu"
                aria-expanded={isMenuOpen}
                onClick={() => setIsMenuOpen((open) => !open)}
              >
                <PlusIcon className="size-5" />
              </Button>
              <Dropdown
                isOpen={isMenuOpen}
                onClose={closeMenu}
                anchorRef={menuButton}
                label="Add to message"
                align="start"
              >
                {attachments && (
                  <DropdownItem Icon={PaperClipIcon} onSelect={() => fileInput.current?.click()}>
                    Add files or photos
                  </DropdownItem>
                )}
                {skills && (
                  <DropdownItem Icon={LanguageIcon} onSelect={() => skillInput.current?.click()}>
                    {skills.uploading ? 'Uploading skill…' : 'Skills'}
                  </DropdownItem>
                )}
              </Dropdown>
              {attachments && (
                <input
                  ref={fileInput}
                  type="file"
                  accept={ATTACHMENT_ACCEPT}
                  multiple
                  hidden
                  data-testid="attachment-input"
                  onChange={handlePick}
                />
              )}
              {skills && (
                <input
                  ref={skillInput}
                  type="file"
                  accept={skills.accept}
                  hidden
                  data-testid="skill-input"
                  onChange={handlePickSkill}
                />
              )}
            </>
          )}
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            role="combobox"
            aria-label="Message"
            aria-autocomplete="list"
            aria-expanded={suggesting}
            aria-controls={suggesting ? suggestionsId : undefined}
            aria-activedescendant={suggesting ? optionId(command.activeIndex) : undefined}
            rows={1}
            placeholder="Type a message..."
            className="h-11 max-h-40 flex-1 resize-none border-none bg-transparent p-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:ring-0"
          />
          {run && (
            <>
              <RunPicker label={`Model: ${run.model}`} value={run.model}>
                {MODELS.map((model) => (
                  <DropdownOption key={model} checked={model === run.model} onSelect={() => run.onModel(model)}>
                    {model}
                  </DropdownOption>
                ))}
              </RunPicker>
              <RunPicker label={`Effort: ${effortLabel(run.effort)}`} value={effortLabel(run.effort)}>
                {EFFORTS.map(({ value, label }) => (
                  <DropdownOption key={value} checked={value === run.effort} onSelect={() => run.onEffort(value)}>
                    {label}
                  </DropdownOption>
                ))}
              </RunPicker>
            </>
          )}
          <Button type="submit" size="icon" aria-label="Send" disabled={!canSend}>
            <PaperAirplaneIcon className="size-4" />
          </Button>
        </div>
      </div>
    </form>
  );
}
