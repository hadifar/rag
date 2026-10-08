import { CheckCircleIcon } from '@heroicons/react/16/solid';
import type { TodoItem } from '@/shared/types';
import type { TodosContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

const STATUS_LABEL: Record<TodoItem['status'], string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Done',
};

const TEXT_STYLE: Record<TodoItem['status'], string> = {
  pending: 'text-slate-500',
  in_progress: 'font-medium text-slate-800',
  completed: 'text-slate-400 line-through',
};

function StatusIcon({ status }: Pick<TodoItem, 'status'>) {
  switch (status) {
    case 'completed':
      return <CheckCircleIcon className="size-3.5 text-success-500" />;
    case 'in_progress':
      return (
        <span className="flex size-3.5 items-center justify-center rounded-full border-[1.5px] border-primary-500">
          <span className="size-1.5 animate-pulse rounded-full bg-primary-500" />
        </span>
      );
    case 'pending':
      return <span className="size-3.5 rounded-full border-[1.5px] border-slate-300" />;
  }
}

export function TodosBubble({ todos }: TodosContent) {
  return (
    <BubbleFrame className="w-[480px]">
      <div className="mb-1 text-xs font-medium text-slate-700">📋 Plan</div>
      <ul aria-label="Plan" className="m-0 list-none rounded-lg p-0 border border-slate-200 bg-white text-xs">
        {todos.map(({ content, status }, index) => (
          <li
            // The agent rewrites the whole list each time, and two todos can read the same.
            key={`${index}:${content}`}
            className="flex items-center gap-2 border-b border-slate-200 px-2.5 py-2 last:border-b-0"
          >
            <span className="flex shrink-0" title={STATUS_LABEL[status]}>
              <StatusIcon status={status} />
            </span>
            <span className={TEXT_STYLE[status]}>{content}</span>
            <span className="sr-only">({STATUS_LABEL[status]})</span>
          </li>
        ))}
      </ul>
    </BubbleFrame>
  );
}
