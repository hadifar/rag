import { useCallback, useState, useTransition } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '@/shared/api/client';
import type { LoginRedirectState } from '../types';
import { useAuth } from './useAuth';

/** Signs in, then returns to the page that sent the user to /login (or home). */
export function useLogin() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const submit = useCallback(
    (email: string, password: string) => {
      setError(null);
      startTransition(async () => {
        // Caught here: an error escaping a transition goes to the route's error page.
        try {
          await login(email, password);
        } catch (err) {
          setError(
            err instanceof ApiError && err.status === 401
              ? 'Invalid email or password'
              : "Couldn't sign in. Please try again."
          );
          return;
        }
        const from = (location.state as LoginRedirectState | null)?.from;
        navigate(from ?? '/', { replace: true });
      });
    },
    [login, navigate, location.state]
  );

  return { submit, error, isPending };
}
