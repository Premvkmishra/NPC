import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { getPlayerId } from "@/lib/api";
import { TabBar } from "./TabBar";
import { ApiBadge } from "./ApiBadge";
import { RestartButton } from "./ResetProfile";
import { LoadingState } from "./States";

export function AppShell({ children, tabs = true }: { children: ReactNode; tabs?: boolean }) {
  const navigate = useNavigate();
  const [ok, setOk] = useState(false);
  useEffect(() => {
    if (!getPlayerId()) navigate({ to: "/onboarding", replace: true });
    else setOk(true);
  }, [navigate]);
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[430px] flex-col paper-bg md:my-6 md:min-h-[calc(100vh-3rem)] md:ink-border md:border-paper">
      <header className="flex items-center justify-between border-b-[3px] border-ink px-4 py-2">
        <span className="font-pixel text-2xl tracking-wider">NPC</span>
        <div className="flex items-center gap-2">
          {ok && <RestartButton />}
          <ApiBadge />
        </div>
      </header>
      <main className="flex-1 space-y-5 px-4 py-5">{ok ? children : <LoadingState />}</main>
      {tabs && <TabBar />}
    </div>
  );
}
