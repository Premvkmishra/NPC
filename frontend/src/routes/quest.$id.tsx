import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { QuestDetails } from "@/pages/QuestDetails";

export const Route = createFileRoute("/quest/$id")({
  head: () => ({ meta: [
    { title: "Side Quest — NPC" }, { name: "description", content: "Your side quest details, why NPC picked it, and how to complete it." },
    { property: "og:title", content: "Side Quest — NPC" }, { property: "og:description", content: "Your side quest details, why NPC picked it, and how to complete it." },
    { property: "og:type", content: "article" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Page,
});

function Page() {
  const { id } = Route.useParams();
  return <AppShell><QuestDetails id={id} /></AppShell>;
}
