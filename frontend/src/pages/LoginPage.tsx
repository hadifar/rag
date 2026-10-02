import { useState, type SubmitEvent } from 'react';

import { useLogin } from '@/features/auth';
import { APP_NAME, BrandMark } from '@/shared/ui/Brand';
import { Button } from '@/shared/ui/Button';
import { TextField } from '@/shared/ui/Input';
import { StatusLine } from '@/shared/ui/StatusLine';

export function LoginPage() {
  const { submit, error, isPending } = useLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    submit(email, password);
  };

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-center gap-3">
          <BrandMark size="lg" />
          <h1 className="text-lg font-semibold text-slate-900">Sign in to {APP_NAME}</h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && (
            <StatusLine tone="error" role="alert">
              {error}
            </StatusLine>
          )}

          <Button type="submit" disabled={isPending} className="mt-2">
            {isPending ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>
      </div>
    </div>
  );
}
