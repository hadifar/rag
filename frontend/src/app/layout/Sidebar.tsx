import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  PencilSquareIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowRightStartOnRectangleIcon,
} from '@heroicons/react/24/outline';

import { useAuth } from '@/features/auth';
import { ConversationList } from '@/features/conversations';
import { APP_NAME, BrandMark } from '@/shared/ui/Brand';
import { IconButton } from '@/shared/ui/IconButton';

type Icon = typeof HomeIcon;
type NavItem = { to: string; label: string; Icon: Icon };

const topLinks: NavItem[] = [{ to: '/', label: 'Home', Icon: HomeIcon }];

const footerLinks: NavItem[] = [{ to: '/settings', label: 'Settings', Icon: Cog6ToothIcon }];

// One look for every sidebar row, link or button; collapsed, only its icon shows.
function itemCls(isCollapsed: boolean, isActive = false) {
  return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isCollapsed ? 'justify-center' : ''
  } ${
    isActive
      ? 'bg-primary-50 text-primary-700'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`;
}

function itemIconCls(isActive = false) {
  return `size-4.5 shrink-0 ${isActive ? 'text-primary-600' : 'text-slate-400'}`;
}

function SidebarLink({ to, label, Icon, isCollapsed }: NavItem & { isCollapsed: boolean }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) => itemCls(isCollapsed, isActive)}
    >
      {({ isActive }) => (
        <>
          <Icon className={itemIconCls(isActive)} />
          {!isCollapsed && label}
        </>
      )}
    </NavLink>
  );
}

function SidebarButton({
  label,
  Icon,
  isCollapsed,
  onClick,
}: { label: string; Icon: Icon; isCollapsed: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={isCollapsed ? label : undefined}
      className={`w-full ${itemCls(isCollapsed)}`}
    >
      <Icon className={itemIconCls()} />
      {!isCollapsed && label}
    </button>
  );
}

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuth();

  const startNewChat = () => navigate('/chat');

  const collapseToggle = (
    <IconButton
      label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      onClick={() => setIsCollapsed((collapsed) => !collapsed)}
    >
      {isCollapsed ? <ChevronRightIcon className="size-4" /> : <ChevronLeftIcon className="size-4" />}
    </IconButton>
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
          <BrandMark />
          {!isCollapsed && (
            <span className="text-sm font-semibold text-slate-900 tracking-tight truncate">
              {APP_NAME}
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
        <SidebarButton
          label="New chat"
          Icon={PencilSquareIcon}
          isCollapsed={isCollapsed}
          onClick={startNewChat}
        />
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
        <SidebarButton
          label="Log out"
          Icon={ArrowRightStartOnRectangleIcon}
          isCollapsed={isCollapsed}
          onClick={() => void handleLogout()}
        />
      </div>
    </aside>
  );
}
