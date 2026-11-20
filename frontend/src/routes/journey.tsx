import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Journey } from "@/pages/Journey";

export const Route = createFileRoute("/journey")({
  head: () => ({ meta: [
    { title: "My Journey — NPC" }, { name: "description", content: "Your level, XP, passport of stamped experiences and achievements." },
    { property: "og:title", content: "My Journey — NPC" }, { property: "og:description", content: "Your level, XP, passport of stamped experiences and achievements." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Page,
});

function Page() {
  return <AppShell><Journey /></AppShell>;
}
