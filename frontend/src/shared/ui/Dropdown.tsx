import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  type ComponentType,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
  type SVGProps,
} from 'react';
import { createPortal } from 'react-dom';

const GAP = 4; // px between the anchor and the menu
const MARGIN = 8; // px the menu keeps from the window's edges

/**
 * Where the menu goes: under the anchor with their right edges lined up, or above it
 * when there's no room below, and kept inside the window.
 */
function menuPosition(anchor: DOMRect, menu: DOMRect): { top: number; left: number } {
  const below = anchor.bottom + GAP;
  const top =
    below + menu.height <= window.innerHeight - MARGIN ? below : anchor.top - GAP - menu.height;
  const left = Math.min(anchor.right - menu.width, window.innerWidth - MARGIN - menu.width);
  return { top: Math.max(MARGIN, top), left: Math.max(MARGIN, left) };
}

/** Closes the menu and hands focus back to its anchor; items call it before acting. */
const CloseContext = createContext<() => void>(() => {});

type DropdownProps = {
  isOpen: boolean;
  onClose: () => void;
  /** The button that opens it: the menu lines up with it, and focus goes back to it. */
  anchorRef: RefObject<HTMLElement | null>;
  /** The menu's accessible name, e.g. "Chat options". */
  label: string;
  /** `DropdownItem`s. */
  children: ReactNode;
};

/**
 * A menu of actions that opens next to its anchor. Arrow keys, Home and End move between
 * the items; Escape, Tab, a click outside, scrolling or resizing close it.
 */
export function Dropdown({ isOpen, onClose, anchorRef, label, children }: DropdownProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    onClose();
    anchorRef.current?.focus();
  }, [onClose, anchorRef]);

  // Before paint, so the menu never shows at its unplaced position.
  useLayoutEffect(() => {
    const menu = menuRef.current;
    const anchor = anchorRef.current;
    if (!isOpen || !menu || !anchor) return;
    const { top, left } = menuPosition(anchor.getBoundingClientRect(), menu.getBoundingClientRect());
    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
    menu.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [isOpen, anchorRef]);

  // Its position is fixed to where the anchor was, so anything that moves the anchor closes it.
  useEffect(() => {
    if (!isOpen) return;
    const closeOnOutsideClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!menuRef.current?.contains(target) && !anchorRef.current?.contains(target)) onClose();
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    window.addEventListener('scroll', onClose, true);
    window.addEventListener('resize', onClose);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      window.removeEventListener('scroll', onClose, true);
      window.removeEventListener('resize', onClose);
    };
  }, [isOpen, onClose, anchorRef]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === 'Tab') {
      onClose();
      return;
    }
    const items = [...(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
    const at = items.indexOf(document.activeElement as HTMLElement);
    const next = {
      ArrowDown: (at + 1) % items.length,
      ArrowUp: (at - 1 + items.length) % items.length,
      Home: 0,
      End: items.length - 1,
    }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    items[next]?.focus();
  };

  if (!isOpen) return null;

  // Portalled so the scrolling sidebar can't clip it.
  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-label={label}
      onKeyDown={onKeyDown}
      className="fixed z-40 box-border w-44 rounded-xl bg-white p-1.5 shadow-lg ring-1 ring-slate-900/10"
    >
      <CloseContext value={close}>{children}</CloseContext>
    </div>,
    document.body
  );
}

const tones = {
  neutral:
    'text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:bg-slate-100 focus-visible:text-slate-900',
  danger: 'text-danger-600 hover:bg-danger-50 focus-visible:bg-danger-50',
};

type DropdownItemProps = {
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** `danger` for a destructive action. */
  tone?: keyof typeof tones;
  /** Runs after the menu has closed. */
  onSelect: () => void;
  children: ReactNode;
};

/** One action in a `Dropdown`. */
export function DropdownItem({ Icon, tone = 'neutral', onSelect, children }: DropdownItemProps) {
  const close = useContext(CloseContext);
  return (
    <button
      type="button"
      role="menuitem"
      tabIndex={-1}
      onClick={() => {
        close();
        onSelect();
      }}
      className={`flex box-border w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors focus:outline-none ${tones[tone]}`}
    >
      <Icon className="size-4 shrink-0" />
      {children}
    </button>
  );
}
