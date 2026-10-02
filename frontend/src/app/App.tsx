import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { AuthProvider, RequireAuth } from '@/features/auth';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { createQueryClient } from '@/shared/api/queryClient';
import { routePatterns, routes } from '@/shared/routes';
import { AppLayout } from './layout/AppLayout';

// The server data every page reads, cached and shared; cleared on logout (see AuthProvider).
const queryClient = createQueryClient();

const router = createBrowserRouter([
  { path: routes.login, element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        path: routes.home,
        element: <AppLayout />,
        children: [
          { index: true, element: <HomePage /> },
          // One route for new (/chat) and existing (/chat/:id) chats. Loaded on first
          // visit: it pulls in the markdown renderer, which no other page needs.
          {
            path: routePatterns.chat,
            lazy: async () => ({ Component: (await import('@/pages/ChatPage')).ChatPage }),
          },
          { path: routes.settings, element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
