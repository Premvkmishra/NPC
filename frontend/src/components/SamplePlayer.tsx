import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { api } from "@/lib/api";
import { Btn } from "./Btn";
import { ErrorState } from "./States";

/** Loads a demo player with ~2 months of quest history, replacing the current save on this device. */
export function SamplePlayerButton({
  label = "Try a sample player",
  variant = "paper",
  className = "",
}: {
  label?: string;
  variant?: "paper" | "butter";
  className?: string;
}) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const load = useMutation({
    mutationFn: () => api.createSamplePlayer(),
    onSuccess: () => {
      qc.clear();
      navigate({ to: "/analytics", replace: true });
    },
  });
  return (
    <div className="space-y-2">
      <Btn
        type="button"
        variant={variant}
        className={`w-full ${className}`}
        disabled={load.isPending}
        onClick={() => load.mutate()}
      >
        {load.isPending ? "Loading sample…" : label}
      </Btn>
      {load.isError && <ErrorState error={load.error} />}
    </div>
  );
}
