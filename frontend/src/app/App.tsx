import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { AuthProvider, RequireAuth } from '@/features/auth';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { AppLayout } from './layout/AppLayout';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <HomePage /> },
          // One route for new (/chat) and existing (/chat/:id) chats. Loaded on first
          // visit: it pulls in the markdown renderer, which no other page needs.
          {
            path: 'chat/:conversationId?',
            lazy: async () => ({ Component: (await import('@/pages/ChatPage')).ChatPage }),
          },
          { path: 'settings', element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
