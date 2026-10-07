import { memo, useCallback, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BookmarkIcon,
  BookmarkSlashIcon,
  EllipsisVerticalIcon,
  PencilIcon,
  ShareIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

import { Dropdown, DropdownItem } from '@/shared/ui/Dropdown';
import { IconButton } from '@/shared/ui/IconButton';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { ConversationResponse } from '@/shared/types';
import { routes } from '@/shared/routes';

// Shown until the conversation's first answer names it.
export const NEW_CHAT_TITLE = 'New chat';

/** The title being edited: Enter saves, Escape or leaving the field cancels. */
function RenameField({
  title,
  isSaving,
  error,
  onSave,
  onCancel,
}: {
  title: string;
  isSaving: boolean;
  error: string | null;
  onSave: (draft: string) => void;
  onCancel: () => void;
}) {
  return (
    <div className="min-w-0 flex-1">
      <input
        aria-label="Chat title"
        defaultValue={title}
        maxLength={200}
        autoFocus
        // Read-only, not disabled, while saving: disabling would drop focus and cancel.
        readOnly={isSaving}
        onFocus={(e) => e.currentTarget.select()}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSave(e.currentTarget.value);
          if (e.key === 'Escape') onCancel();
        }}
        onBlur={onCancel}
        className="box-border w-full rounded-lg border border-primary-300 bg-white px-3 py-2 text-[13px] text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
      {error && (
        <StatusLine role="alert" tone="error" size="sm" className="px-1 pt-1">
          {error}
        </StatusLine>
      )}
    </div>
  );
}

type ConversationRowProps = {
  conversation: ConversationResponse;
  /** Deleted: it plays its exit, then `onVanished` takes it off the list. */
  vanishing: boolean;
  onVanished: (id: string) => void;
  isRenaming: boolean;
  isSavingRename: boolean;
  renameError: string | null;
  onTogglePin: (conversation: ConversationResponse) => void;
  onStartRename: (conversation: ConversationResponse) => void;
  onSaveRename: (conversation: ConversationResponse, draft: string) => void;
  onCancelRename: () => void;
  onShare: (conversation: ConversationResponse) => void;
  onDelete: (conversation: ConversationResponse) => void;
};

/** One chat in the sidebar: a link to it, and a menu to pin, rename, share or delete it. */
export const ConversationRow = memo(function ConversationRow({
  conversation,
  vanishing,
  onVanished,
  isRenaming,
  isSavingRename,
  renameError,
  onTogglePin,
  onStartRename,
  onSaveRename,
  onCancelRename,
  onShare,
  onDelete,
}: ConversationRowProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const closeMenu = useCallback(() => setIsMenuOpen(false), []);
  const menuButton = useRef<HTMLButtonElement>(null);
  const title = conversation.title ?? NEW_CHAT_TITLE;
  // The empty draft has nothing to pin, name or share yet: its first message names it.
  const isDraft = conversation.title === null;

  if (isRenaming) {
    return (
      <RenameField
        title={title}
        isSaving={isSavingRename}
        error={renameError}
        onSave={(draft) => onSaveRename(conversation, draft)}
        onCancel={onCancelRename}
      />
    );
  }

  return (
    <div
      className={`group flex items-center gap-1 ${vanishing ? 'pointer-events-none animate-vaporize' : ''}`}
      // Already deleted: hidden from assistive tech while it plays its exit.
      aria-hidden={vanishing || undefined}
      onAnimationEnd={vanishing ? () => onVanished(conversation.id) : undefined}
    >
      <NavLink
        to={routes.chat(conversation.id)}
        title={title}
        className={({ isActive }) =>
          `min-w-0 flex-1 truncate rounded-lg py-2.5 pl-3 pr-1 text-left text-[13px] transition-colors ${
            isActive
              ? 'bg-slate-100 font-medium text-slate-900'
              : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
          }`
        }
      >
        {title}
      </NavLink>
      <IconButton
        ref={menuButton}
        label="Chat options"
        aria-haspopup="menu"
        aria-expanded={isMenuOpen}
        onClick={() => setIsMenuOpen((open) => !open)}
        // Shown on hovering its row, on reaching it by keyboard, or while its menu is open.
        className={isMenuOpen ? '' : 'opacity-0 focus:opacity-100 group-hover:opacity-100'}
      >
        <EllipsisVerticalIcon className="size-4" />
      </IconButton>
      <Dropdown
        isOpen={isMenuOpen}
        onClose={closeMenu}
        anchorRef={menuButton}
        label="Chat options"
      >
        {!isDraft && (
          <DropdownItem
            Icon={conversation.pinned_at ? BookmarkSlashIcon : BookmarkIcon}
            onSelect={() => onTogglePin(conversation)}
          >
            {conversation.pinned_at ? 'Unpin' : 'Pin'}
          </DropdownItem>
        )}
        {!isDraft && (
          <DropdownItem Icon={PencilIcon} onSelect={() => onStartRename(conversation)}>
            Rename
          </DropdownItem>
        )}
        {!isDraft && (
          <DropdownItem Icon={ShareIcon} onSelect={() => onShare(conversation)}>
            Share
          </DropdownItem>
        )}
        <DropdownItem Icon={TrashIcon} tone="danger" onSelect={() => onDelete(conversation)}>
          Delete
        </DropdownItem>
      </Dropdown>
    </div>
  );
});
