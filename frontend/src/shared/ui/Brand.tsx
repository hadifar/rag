import { SparklesIcon } from '@heroicons/react/24/outline';

export const APP_NAME = 'RAG Chat';

const sizes = {
  sm: { box: 'size-7 rounded-lg', icon: 'size-4' },
  lg: { box: 'size-10 rounded-lg', icon: 'size-5' },
};

/** The app's logo mark. */
export function BrandMark({ size = 'sm' }: { size?: keyof typeof sizes }) {
  return (
    <div className={`flex shrink-0 items-center justify-center bg-primary-600 ${sizes[size].box}`}>
      <SparklesIcon className={`text-white ${sizes[size].icon}`} />
    </div>
  );
}
