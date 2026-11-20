import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function ApiBadge() {
  const { data, isError } = useQuery({ queryKey: ["health"], queryFn: () => api.health(), staleTime: 60_000 });
  const label = isError ? "offline" : !data ? "…" : data.mock_mode ? "mock" : "live";
  return <span className="border-2 border-ink bg-card px-1.5 font-mono text-[10px] uppercase">API: {label}</span>;
}
