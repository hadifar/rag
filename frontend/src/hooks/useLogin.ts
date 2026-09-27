import { useCallback, useState, useTransition } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

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
        } catch {
          setError('Invalid email or password');
          return;
        }
        const from = (location.state as { from?: { pathname: string } } | null)?.from;
        navigate(from?.pathname ?? '/', { replace: true });
      });
    },
    [login, navigate, location.state]
  );

  return { submit, error, isPending };
}
