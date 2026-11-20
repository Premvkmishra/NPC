import type { ButtonHTMLAttributes } from "react";
const V = { primary: "bg-lime", butter: "bg-butter", orange: "bg-orange", paper: "bg-card", ink: "bg-ink text-paper" } as const;
export function Btn({ variant = "primary", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof V }) {
  return <button {...p} className={`min-h-11 ink-border btn-press px-4 py-2 font-pixel text-base uppercase tracking-wider disabled:opacity-60 ${V[variant]} ${className}`} />;
}
