import { memo } from 'react';
import { NavLink } from 'react-router-dom';
import { TrashIcon } from '@heroicons/react/24/outline';

import { ConfirmDeleteModal } from '@/shared/ui/ConfirmDeleteModal';
import type { ConversationResponse } from '@/shared/types';
import { useConversations } from '../hooks/useConversations';
import { useConfirmDeleteConversation } from '../hooks/useConfirmDeleteConversation';
import { conversationPath } from '../model/conversations';

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
        to={conversationPath(conversation.id)}
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
      <button
        type="button"
        onClick={() => onDelete(conversation)}
        title="Delete chat"
        className="shrink-0 rounded-md p-1 text-slate-400 opacity-0 transition-opacity hover:bg-slate-200 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
      >
        <TrashIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
});

/** The sidebar's recent chats: paged in on demand, each deletable after a confirmation. */
export function ConversationList() {
  const { conversations, status, hasMore, isLoadingMore, loadMore } = useConversations();
  const { requestDelete, pending, isDeleting, error, confirm, cancel } =
    useConfirmDeleteConversation();

  return (
    <>
      <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-400">Recent</p>
      {status === 'loading' && <p className="px-3 py-2 text-[13px] text-slate-400">Loading…</p>}
      {status === 'error' && (
        <p className="px-3 py-2 text-[13px] text-slate-400">Couldn't load your chats.</p>
      )}
      {status === 'ready' && conversations.length === 0 && (
        <p className="px-3 py-2 text-[13px] text-slate-400">No chats yet.</p>
      )}
      {conversations.map((conversation) => (
        <ConversationLink key={conversation.id} conversation={conversation} onDelete={requestDelete} />
      ))}
      {hasMore && (
        <button
          type="button"
          onClick={loadMore}
          disabled={isLoadingMore}
          className="w-full rounded-lg px-3 py-2 text-left text-[13px] text-indigo-600 hover:bg-slate-50 disabled:text-slate-400"
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
