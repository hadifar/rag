import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../../context/AuthContext';

export default function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return null;
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
