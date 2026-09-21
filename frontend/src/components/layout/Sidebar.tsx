import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Chat', end: true },
  { to: '/settings', label: 'Settings', end: false },
];

export default function Sidebar() {
  return (
    <nav className="flex w-52 shrink-0 flex-col gap-1 border-r border-gray-500/25 px-3 py-4">
      <div className="px-2 pb-3 pt-1 font-semibold">RAG</div>
      {links.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `rounded-md px-2.5 py-2 text-sm hover:bg-gray-500/10 ${
              isActive ? 'bg-gray-500/20 font-medium' : ''
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
