import { Link } from 'react-router-dom';

import { routes } from '@/shared/routes';

export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <h1 className="text-5xl font-bold">404</h1>
      <p>Page not found</p>
      <Link to={routes.home} className="text-primary-600 hover:underline">
        Back home
      </Link>
    </div>
  );
}
