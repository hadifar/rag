import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <h1 className="text-5xl font-bold">404</h1>
      <p>Page not found</p>
      <Link to="/" className="text-indigo-600 hover:underline">
        Back to chat
      </Link>
    </div>
  );
}
