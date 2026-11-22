import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { clearPlayer } from "@/lib/api";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

/** Forget the current player, drop cached data, and go back to onboarding. */
export function useRestart() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return () => {
    clearPlayer();
    qc.clear();
    navigate({ to: "/onboarding", replace: true });
  };
}

const btn = "min-h-11 rounded-none ink-border btn-press px-4 py-2 font-pixel text-base uppercase tracking-wider text-ink shadow-none";

/** Header chip that lets the player start over at any time, after a confirmation. */
export function RestartButton() {
  const restart = useRestart();
  return (
    <AlertDialog>
      <AlertDialogTrigger className="border-2 border-ink bg-card px-1.5 font-mono text-[10px] uppercase hover:bg-butter focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink">
        ↺ Restart
      </AlertDialogTrigger>
      <AlertDialogContent className="max-w-[360px] rounded-none ink-border bg-paper shadow-hard">
        <AlertDialogHeader>
          <AlertDialogTitle className="font-pixel text-2xl">Start a new save file?</AlertDialogTitle>
          <AlertDialogDescription className="text-sm text-ink">
            This erases your level, XP, passport and badges on this device, then takes you back to onboarding. You can't undo it.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="grid grid-cols-2 gap-3 sm:space-x-0">
          <AlertDialogCancel className={`${btn} mt-0 bg-card hover:bg-card`}>Keep playing</AlertDialogCancel>
          <AlertDialogAction className={`${btn} bg-orange hover:bg-orange`} onClick={restart}>Erase &amp; restart</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
