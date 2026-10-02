import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import type { LoginRedirectState } from '../types';

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return null;
  }

  if (status === 'unauthenticated') {
    const state: LoginRedirectState = {
      from: location.pathname + location.search + location.hash,
    };
    return <Navigate to="/login" state={state} replace />;
  }

  return <Outlet />;
}
