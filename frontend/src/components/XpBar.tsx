export function XpBar({ value, max = 1000, segments = 10 }: { value: number; max?: number; segments?: number }) {
  const filled = Math.floor((value / max) * segments);
  return (
    <div role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} aria-label="XP in level" className="flex gap-1 ink-border bg-card p-1">
      {Array.from({ length: segments }, (_, i) => (
        <div key={i} className={`h-4 flex-1 ${i < filled ? "bg-butter" : "bg-paper-deep"} ${i < filled ? "animate-pop" : ""}`} style={{ animationDelay: `${i * 60}ms` }} />
      ))}
    </div>
  );
}
