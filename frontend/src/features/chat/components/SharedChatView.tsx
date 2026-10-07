import { Link } from 'react-router-dom';

import { APP_NAME, BrandMark } from '@/shared/ui/Brand';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { LoadStatus } from '@/shared/types';
import { routes } from '@/shared/routes';
import type { Bubble } from '../types';
import { MessageList } from './MessageList';

type SharedChatViewProps = {
  status: LoadStatus;
  title: string | null;
  sharedOn: string | null;
  bubbles: Bubble[];
  error: string | null;
};

/** A shared chat, read-only: its title and date above the messages, and no composer. */
export function SharedChatView({ status, title, sharedOn, bubbles, error }: SharedChatViewProps) {
  return (
    <div className="flex h-full flex-col bg-white">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-100 px-4 py-3">
        <Link to={routes.home} aria-label={APP_NAME}>
          <BrandMark />
        </Link>
        <div className="min-w-0">
          <h1 className="m-0 truncate text-sm font-semibold text-slate-900">{title ?? APP_NAME}</h1>
          {sharedOn && (
            <p className="m-0 text-xs text-slate-500">Shared on {sharedOn} · read-only</p>
          )}
        </div>
      </header>
      {status === 'loading' && (
        <StatusLine size="sm" className="px-4 py-6">
          Loading…
        </StatusLine>
      )}
      {status === 'error' && (
        <StatusLine role="alert" tone="error" size="sm" className="px-4 py-6">
          {error}
        </StatusLine>
      )}
      {status === 'ready' && <MessageList bubbles={bubbles} isWaiting={false} />}
    </div>
  );
}
