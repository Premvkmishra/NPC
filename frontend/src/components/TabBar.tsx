import { Link } from "@tanstack/react-router";
import { PixelIcon } from "./PixelIcon";

const TABS = [
  { to: "/", label: "Home", icon: "home" },
  { to: "/explore", label: "Explore", icon: "map" },
  { to: "/journey", label: "Journey", icon: "book" },
] as const;

export function TabBar() {
  return (
    <nav aria-label="Main" className="sticky bottom-0 z-20 grid grid-cols-3 gap-2 border-t-[3px] border-ink bg-ink p-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))]">
      {TABS.map((t) => (
        <Link key={t.to} to={t.to} activeOptions={{ exact: t.to === "/" }}
          className="flex min-h-14 flex-col items-center justify-center gap-0.5 border-[3px] border-paper bg-card text-ink shadow-[0_4px_0_var(--paper-deep)] data-[status=active]:translate-y-1 data-[status=active]:bg-lime data-[status=active]:shadow-none">
          <PixelIcon name={t.icon} size={20} />
          <span className="hud-label">{t.label}</span>
        </Link>
      ))}
    </nav>
  );
}
