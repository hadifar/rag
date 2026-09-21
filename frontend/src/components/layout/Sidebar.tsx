import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

type NavItem = { to: string; label: string; Icon: typeof SparklesIcon };

const mainLinks: NavItem[] = [{ to: '/', label: 'Chat', Icon: ChatBubbleLeftRightIcon }];
const footerLinks: NavItem[] = [{ to: '/settings', label: 'Settings', Icon: Cog6ToothIcon }];

function SidebarLink({ to, label, Icon, isCollapsed }: NavItem & { isCollapsed: boolean }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium no-underline transition-colors ${
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
            className={`shrink-0 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`}
            style={{ height: '1.125rem', width: '1.125rem' }}
          />
          {!isCollapsed && label}
        </>
      )}
    </NavLink>
  );
}

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);

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
        {!isCollapsed && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="shrink-0 p-1 rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            title="Collapse sidebar"
          >
            <ChevronLeftIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Expand button (collapsed state) */}
      {isCollapsed && (
        <div className="flex justify-center py-2 border-b border-slate-100 shrink-0">
          <button
            onClick={() => setIsCollapsed(false)}
            className="p-1 rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            title="Expand sidebar"
          >
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
        {mainLinks.map((link) => (
          <SidebarLink key={link.to} {...link} isCollapsed={isCollapsed} />
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-100 px-2 py-3 space-y-0.5 shrink-0">
        {footerLinks.map((link) => (
          <SidebarLink key={link.to} {...link} isCollapsed={isCollapsed} />
        ))}
      </div>
    </aside>
  );
}
