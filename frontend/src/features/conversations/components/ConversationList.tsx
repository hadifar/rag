import { memo } from 'react';
import { NavLink } from 'react-router-dom';
import { TrashIcon } from '@heroicons/react/24/outline';

import { ConfirmDeleteModal } from '@/shared/ui/ConfirmDeleteModal';
import { IconButton } from '@/shared/ui/IconButton';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { ConversationResponse } from '@/shared/types';
import { routes } from '@/shared/routes';
import { useConversationList } from '../hooks/useConversationList';
import { useConfirmDeleteConversation } from '../hooks/useConfirmDeleteConversation';

// Shown until the conversation's first answer names it.
const NEW_CHAT_TITLE = 'New chat';

const ConversationLink = memo(function ConversationLink({
  conversation,
  onDelete,
}: {
  conversation: ConversationResponse;
  onDelete: (conversation: ConversationResponse) => void;
}) {
  return (
    <div className="group flex items-center gap-1">
      <NavLink
        to={routes.chat(conversation.id)}
        title={conversation.title ?? NEW_CHAT_TITLE}
        className={({ isActive }) =>
          `min-w-0 flex-1 truncate rounded-lg px-3 py-2.5 text-left text-[13px] transition-colors ${
            isActive
              ? 'bg-slate-100 font-medium text-slate-900'
              : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
          }`
        }
      >
        {conversation.title ?? NEW_CHAT_TITLE}
      </NavLink>
      <IconButton
        label="Delete chat"
        tone="danger"
        onClick={() => onDelete(conversation)}
        // Shown on hovering its row, or on reaching it by keyboard.
        className="opacity-0 focus:opacity-100 group-hover:opacity-100"
      >
        <TrashIcon className="size-3.5" />
      </IconButton>
    </div>
  );
});

/** The sidebar's recent chats: paged in on demand, each deletable after a confirmation. */
export function ConversationList() {
  const { conversations, status, hasMore, isLoadingMore, loadMore } = useConversationList();
  const { requestDelete, pending, isDeleting, error, confirm, cancel } =
    useConfirmDeleteConversation();

  return (
    <>
      <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-400">Recent</p>
      {status === 'loading' && (
        <StatusLine size="sm" className="px-3 py-2">
          Loading…
        </StatusLine>
      )}
      {status === 'error' && (
        <StatusLine size="sm" className="px-3 py-2">
          Couldn't load your chats.
        </StatusLine>
      )}
      {status === 'ready' && conversations.length === 0 && (
        <StatusLine size="sm" className="px-3 py-2">
          No chats yet.
        </StatusLine>
      )}
      {conversations.map((conversation) => (
        <ConversationLink key={conversation.id} conversation={conversation} onDelete={requestDelete} />
      ))}
      {hasMore && (
        <button
          type="button"
          onClick={loadMore}
          disabled={isLoadingMore}
          className="w-full rounded-lg px-3 py-2 text-left text-[13px] text-primary-600 hover:bg-slate-50 disabled:text-slate-400"
        >
          {isLoadingMore ? 'Loading…' : 'Load more'}
        </button>
      )}
      <ConfirmDeleteModal
        isOpen={pending !== null}
        title="Delete chat?"
        message={
          <>
            <span className="font-medium text-slate-700">
              “{pending?.title ?? NEW_CHAT_TITLE}”
            </span>{' '}
            will be permanently deleted. This can't be undone.
          </>
        }
        isBusy={isDeleting}
        error={error}
        onConfirm={confirm}
        onCancel={cancel}
      />
    </>
  );
}
