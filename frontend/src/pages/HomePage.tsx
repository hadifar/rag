import { useAuth } from '../context/AuthContext';

export function HomePage() {
  const { user } = useAuth();

  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <h1 className="text-3xl font-semibold text-slate-900">Hello {user?.email}</h1>
    </div>
  );
}
