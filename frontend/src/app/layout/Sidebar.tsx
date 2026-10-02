import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  PencilSquareIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
  ArrowRightStartOnRectangleIcon,
} from '@heroicons/react/24/outline';

import { useAuth } from '@/features/auth';
import { ConversationList } from '@/features/conversations';

type NavItem = { to: string; label: string; Icon: typeof SparklesIcon };

const topLinks: NavItem[] = [{ to: '/', label: 'Home', Icon: HomeIcon }];

const footerLinks: NavItem[] = [{ to: '/settings', label: 'Settings', Icon: Cog6ToothIcon }];

function SidebarLink({ to, label, Icon, isCollapsed }: NavItem & { isCollapsed: boolean }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isCollapsed ? 'justify-center' : ''
        } ${
          isActive
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            className={`size-4.5 shrink-0 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`}
          />
          {!isCollapsed && label}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuth();

  const startNewChat = () => navigate('/chat');

  const collapseToggle = (
    <button
      onClick={() => setIsCollapsed((collapsed) => !collapsed)}
      className="shrink-0 rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
      title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
    >
      {isCollapsed ? (
        <ChevronRightIcon className="h-4 w-4" />
      ) : (
        <ChevronLeftIcon className="h-4 w-4" />
      )}
    </button>
  );

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <aside
      className={`${
        isCollapsed ? 'w-16' : 'w-60'
      } shrink-0 bg-white border-r border-slate-200 flex flex-col transition-all duration-300 overflow-hidden`}
    >
      {/* Brand */}
      <div className="h-16 flex items-center px-3 border-b border-slate-100 shrink-0">
        <div
          className={`flex items-center gap-2.5 flex-1 min-w-0 ${isCollapsed ? 'justify-center' : ''}`}
        >
          <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
            <SparklesIcon className="h-4 w-4 text-white" />
          </div>
          {!isCollapsed && (
            <span className="text-sm font-semibold text-slate-900 tracking-tight truncate">
              RAG Chat
            </span>
          )}
        </div>
        {!isCollapsed && collapseToggle}
      </div>

      {/* Expand button (collapsed state) */}
      {isCollapsed && (
        <div className="flex justify-center py-2 border-b border-slate-100 shrink-0">
          {collapseToggle}
        </div>
      )}

      {/* Home */}
      <div className="px-2 pt-4 shrink-0 space-y-0.5">
        {topLinks.map((link) => (
          <SidebarLink key={link.to} {...link} isCollapsed={isCollapsed} />
        ))}
      </div>

      {/* New chat */}
      <div className="px-2 pt-2 shrink-0">
        <button
          onClick={startNewChat}
          title={isCollapsed ? 'New chat' : undefined}
          className={`w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
        >
          <PencilSquareIcon
            className="size-4.5 shrink-0 text-slate-400"
          />
          {!isCollapsed && 'New chat'}
        </button>
      </div>

      <div className="mx-3 my-3 border-t border-slate-100 shrink-0" />

      {/* Previous sessions */}
      <nav className="flex-1 px-2 pb-2 space-y-0.5 overflow-y-auto min-h-0">
        {!isCollapsed && <ConversationList />}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-100 px-2 py-3 space-y-0.5 shrink-0">
        {footerLinks.map((link) => (
          <SidebarLink key={link.to} {...link} isCollapsed={isCollapsed} />
        ))}
        <button
          onClick={handleLogout}
          title={isCollapsed ? 'Log out' : undefined}
          className={`w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
        >
          <ArrowRightStartOnRectangleIcon
            className="size-4.5 shrink-0 text-slate-400"
          />
          {!isCollapsed && 'Log out'}
        </button>
      </div>
    </aside>
  );
}
