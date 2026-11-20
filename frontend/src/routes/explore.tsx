import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Explore } from "@/pages/Explore";

export const Route = createFileRoute("/explore")({
  head: () => ({ meta: [
    { title: "Explore Quests — NPC" }, { name: "description", content: "Browse side quests by category and discover real places near you." },
    { property: "og:title", content: "Explore Quests — NPC" }, { property: "og:description", content: "Browse side quests by category and discover real places near you." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Page,
});

function Page() {
  return <AppShell><Explore /></AppShell>;
}
