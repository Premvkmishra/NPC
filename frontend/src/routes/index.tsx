import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Home } from "@/pages/Home";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "NPC — Today's Side Quest" }, { name: "description", content: "You're not an NPC. Stop living like one. Your daily real-world side quest." },
    { property: "og:title", content: "NPC — Today's Side Quest" }, { property: "og:description", content: "You're not an NPC. Stop living like one. Your daily real-world side quest." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Page,
});

function Page() {
  return <AppShell><Home /></AppShell>;
}
