import type { ReactNode } from 'react';

import { ConfirmDeleteModal } from '@/shared/ui/ConfirmDeleteModal';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { ConversationResponse } from '@/shared/types';
import { useConversationList } from '../hooks/useConversationList';
import { usePinnedConversations } from '../hooks/usePinnedConversations';
import { useConfirmDeleteConversation } from '../hooks/useConfirmDeleteConversation';
import { useEditConversation } from '../hooks/useEditConversation';
import { useShareConversation } from '../hooks/useShareConversation';
import { ConversationRow, NEW_CHAT_TITLE } from './ConversationRow';
import { ShareDialog } from './ShareDialog';

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
      {children}
    </p>
  );
}

/**
 * The sidebar's chats: the pinned ones, then the recent ones paged in on demand. Each
 * can be pinned, renamed, shared, or deleted after a confirmation, from its menu.
 */
export function ConversationList() {
  const { conversations, status, hasMore, isLoadingMore, loadMore } = useConversationList();
  const { pinned } = usePinnedConversations();
  const { requestDelete, pending, isDeleting, error, confirm, cancel, vanishing, finishVanish } =
    useConfirmDeleteConversation();
  const {
    togglePin,
    pinError,
    renamingId,
    startRename,
    saveRename,
    cancelRename,
    isSavingRename,
    renameError,
  } = useEditConversation();
  const share = useShareConversation();

  const row = (conversation: ConversationResponse) => {
    const isRenaming = renamingId === conversation.id;
    return (
      <ConversationRow
        key={conversation.id}
        conversation={conversation}
        vanishing={vanishing.has(conversation.id)}
        onVanished={finishVanish}
        isRenaming={isRenaming}
        isSavingRename={isRenaming && isSavingRename}
        renameError={isRenaming ? renameError : null}
        onTogglePin={togglePin}
        onStartRename={startRename}
        onSaveRename={saveRename}
        onCancelRename={cancelRename}
        onShare={share.open}
        onDelete={requestDelete}
      />
    );
  };

  return (
    <>
      {pinError && (
        <StatusLine role="alert" tone="error" size="sm" className="px-3 pb-2">
          {pinError}
        </StatusLine>
      )}
      {pinned.length > 0 && (
        <div className="pb-3">
          <SectionLabel>Pinned</SectionLabel>
          {pinned.map(row)}
        </div>
      )}
      {/* With every chat pinned, an empty "Recent" says nothing. */}
      {!(status === 'ready' && conversations.length === 0 && pinned.length > 0) && (
        <SectionLabel>Recent</SectionLabel>
      )}
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
      {status === 'ready' && conversations.length === 0 && pinned.length === 0 && (
        <StatusLine size="sm" className="px-3 py-2">
          No chats yet.
        </StatusLine>
      )}
      {conversations.map(row)}
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
      <ShareDialog
        isOpen={share.sharing !== null}
        title={share.sharing?.title ?? NEW_CHAT_TITLE}
        status={share.status}
        link={share.link}
        sharedOn={share.sharedOn}
        isSaving={share.isSaving}
        isStopping={share.isStopping}
        copied={share.copied}
        error={share.error}
        onSave={share.saveShare}
        onStop={share.stopSharing}
        onCopy={share.copy}
        onClose={share.close}
      />
    </>
  );
}
