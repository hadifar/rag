import { CheckCircleIcon } from '@heroicons/react/16/solid';
import type { TodoItem, TodosContent } from '../../types';

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
      return <CheckCircleIcon className="size-4 text-emerald-500" />;
    case 'in_progress':
      return (
        <span className="flex size-4 items-center justify-center rounded-full border-[1.5px] border-indigo-500">
          <span className="size-1.5 animate-pulse rounded-full bg-indigo-500" />
        </span>
      );
    case 'pending':
      return <span className="size-4 rounded-full border-[1.5px] border-slate-300" />;
  }
}

export function TodosBubble({ todos }: TodosContent) {
  return (
    <div className="w-full max-w-[480px] px-3 text-sm">
      <div className="mb-1.5 font-medium text-slate-700">📋 Plan</div>
      <ul aria-label="Plan" className="rounded-lg border border-slate-200 bg-white">
        {todos.map(({ content, status }, index) => (
          <li
            // The agent rewrites the whole list each time, and two todos can read the same.
            key={`${index}:${content}`}
            className="flex items-center gap-2 border-b border-slate-200 px-3 py-2.5 last:border-b-0"
          >
            <span className="flex shrink-0" title={STATUS_LABEL[status]}>
              <StatusIcon status={status} />
            </span>
            <span className={TEXT_STYLE[status]}>{content}</span>
            <span className="sr-only">({STATUS_LABEL[status]})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
