import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api, setPlayerId } from "@/lib/api";
import type { Autopilot, Interest, Preferences } from "@/lib/types";
import { Btn } from "@/components/Btn";
import { DialogueBox } from "@/components/DialogueBox";
import { AutopilotMeter } from "@/components/AutopilotMeter";
import { ErrorState, LoadingState } from "@/components/States";
import { SamplePlayerButton } from "@/components/SamplePlayer";

const INTERESTS: { v: Interest; l: string }[] = [
  { v: "food", l: "Food & new places" }, { v: "art", l: "Art & creativity" }, { v: "people", l: "Meeting people" },
  { v: "learning", l: "Learning new things" }, { v: "outdoors", l: "Adventure & outdoors" }, { v: "culture", l: "Culture & local life" },
];

function Choice<T extends string>({ options, value, onChange, label }: { options: { v: T; l: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <fieldset className="space-y-2">
      <legend className="hud-label mb-2">{label}</legend>
      <div className="grid grid-cols-2 gap-2">
        {options.map((o) => (
          <button type="button" key={o.v} aria-pressed={value === o.v} onClick={() => onChange(o.v)}
            className={`min-h-11 ink-border px-2 py-2 text-sm font-semibold ${value === o.v ? "bg-lime translate-x-0.5 translate-y-0.5" : "bg-card shadow-hard-sm"}`}>{o.l}</button>
        ))}
      </div>
    </fieldset>
  );
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block space-y-1"><span className="hud-label">{label}</span>{children}</label>;
}
const input = "w-full min-h-11 ink-border bg-card px-3 py-2 font-mono text-sm";

export function Onboarding() {
  const [step, setStep] = useState(0);
  const [p, setP] = useState<Preferences>({
    display_name: "", interests: [], novelty_frequency: "monthly", social_style: "either", comfort_level: 3,
    city: "Andheri, Mumbai", lat: null, lng: null, free_time_minutes: 60, max_distance_km: 5, budget_inr: 300,
    accessibility_notes: null, last_first_time: "this_month",
  });
  const [result, setResult] = useState<Autopilot | null>(null);
  const [geo, setGeo] = useState("");
  const set = <K extends keyof Preferences>(k: K, v: Preferences[K]) => setP((s) => ({ ...s, [k]: v }));
  const create = useMutation({
    mutationFn: () => api.createPlayer(p),
    onSuccess: (r) => {
      if (r?.player?.id) {
        setPlayerId(r.player.id);
      }
      setResult(r.autopilot);
    },
  });

  const canNext = [p.interests.length > 0, true, p.city.trim().length > 0, p.display_name.trim().length > 0][step];

  if (create.isPending || (create.isSuccess && !result)) {
    return <div className="py-16 text-center"><h1 className="text-3xl">Loading your life…</h1><LoadingState label="Scanning routines" /></div>;
  }
  if (result) {
    return (
      <div className="space-y-5 py-4">
        <h1 className="text-3xl">First reading</h1>
        <AutopilotMeter autopilot={result} />
        <DialogueBox typewriter text={`Welcome, ${p.display_name}. You're not an NPC. Let's find your first side quest.`} />
        <Link to="/" className="block min-h-11 ink-border btn-press bg-lime px-4 py-3 text-center font-pixel uppercase tracking-wider">Start playing</Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-4xl leading-none">NPC</h1>
        <p className="mt-1 text-sm">You're not an NPC. Stop living like one.</p>
      </div>
      <div className="flex gap-1.5" aria-label={`Step ${step + 1} of 4`}>
        {[0, 1, 2, 3].map((i) => <div key={i} className={`h-5 flex-1 ink-border ${i <= step ? "bg-lime" : "bg-card"}`} />)}
      </div>

      {step === 0 && (
        <section className="space-y-3">
          <DialogueBox typewriter text="What sounds like fun to you? Pick as many as you like." />
          <div className="grid grid-cols-2 gap-3">
            {INTERESTS.map((o) => {
              const on = p.interests.includes(o.v);
              return (
                <button key={o.v} type="button" aria-pressed={on}
                  onClick={() => set("interests", on ? p.interests.filter((x) => x !== o.v) : [...p.interests, o.v])}
                  className={`min-h-20 ink-border p-3 text-left font-pixel text-base leading-tight ${on ? "bg-butter translate-x-1 translate-y-1" : "bg-card shadow-hard"}`}>{o.l}</button>
              );
            })}
          </div>
        </section>
      )}
      {step === 1 && (
        <section className="space-y-5">
          <DialogueBox text="Tell me about your routine. No wrong answers." />
          <Choice label="How often do you try something new?" value={p.novelty_frequency} onChange={(v) => set("novelty_frequency", v)}
            options={[{ v: "rarely", l: "Rarely" }, { v: "monthly", l: "Monthly" }, { v: "weekly", l: "Weekly" }, { v: "daily", l: "Daily" }]} />
          <Choice label="Social style" value={p.social_style} onChange={(v) => set("social_style", v)}
            options={[{ v: "solo", l: "Solo" }, { v: "friends", l: "With friends" }, { v: "either", l: "Either" }]} />
          <Field label={`Comfort zone stretch: ${p.comfort_level}/5`}>
            <input type="range" min={1} max={5} value={p.comfort_level} onChange={(e) => set("comfort_level", Number(e.target.value))} className="w-full accent-[var(--ink)]" />
            <span className="flex justify-between hud-label text-muted-foreground"><span>Keep it gentle</span><span>Push me</span></span>
          </Field>
        </section>
      )}
      {step === 2 && (
        <section className="space-y-4">
          <DialogueBox text="Set your boundaries. I'll stay inside them." />
          <Field label="City"><input className={input} value={p.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <button type="button" className="min-h-11 border-2 border-ink bg-card px-3 text-sm underline"
            onClick={() => navigator.geolocation?.getCurrentPosition((pos) => { set("lat", pos.coords.latitude); set("lng", pos.coords.longitude); setGeo("Location saved."); }, () => setGeo("Couldn't get location. City is enough."))}>
            Use my location
          </button>
          {geo && <p className="text-xs">{geo}</p>}
          <div className="grid grid-cols-3 gap-2">
            <Field label="Free min"><input type="number" min={15} max={480} className={input} value={p.free_time_minutes} onChange={(e) => set("free_time_minutes", Math.min(480, Math.max(15, Number(e.target.value))))} /></Field>
            <Field label="Max km"><input type="number" min={0} className={input} value={p.max_distance_km} onChange={(e) => set("max_distance_km", Number(e.target.value))} /></Field>
            <Field label="Budget ₹"><input type="number" min={0} className={input} value={p.budget_inr} onChange={(e) => set("budget_inr", Math.round(Number(e.target.value)))} /></Field>
          </div>
          <Field label="Accessibility notes (optional)"><textarea className={input} rows={2} value={p.accessibility_notes ?? ""} onChange={(e) => set("accessibility_notes", e.target.value || null)} /></Field>
        </section>
      )}
      {step === 3 && (
        <section className="space-y-5">
          <DialogueBox typewriter text="When was the last time you did something for the first time?" />
          <Choice label="Be honest" value={p.last_first_time} onChange={(v) => set("last_first_time", v)}
            options={[{ v: "this_week", l: "This week" }, { v: "this_month", l: "This month" }, { v: "this_year", l: "This year" }, { v: "cant_remember", l: "Can't remember" }]} />
          <Field label="Your player name"><input className={input} value={p.display_name} maxLength={40} onChange={(e) => set("display_name", e.target.value)} placeholder="e.g. Riya" /></Field>
        </section>
      )}

      {create.isError && <ErrorState error={create.error} />}
      <div className="flex gap-3">
        {step > 0 && <Btn variant="paper" onClick={() => setStep(step - 1)}>Back</Btn>}
        <Btn className="flex-1" disabled={!canNext} onClick={() => (step < 3 ? setStep(step + 1) : create.mutate())}>{step < 3 ? "Next" : "Begin"}</Btn>
      </div>
      {step === 0 && (
        <div className="space-y-2 border-t-[3px] border-dashed border-ink pt-4">
          <p className="text-sm">Just looking around? Jump in as a sample player with two months of adventures already logged.</p>
          <SamplePlayerButton />
        </div>
      )}
    </div>
  );
}
