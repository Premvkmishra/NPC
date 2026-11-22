import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Analytics } from "@/pages/Analytics";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "My Stats — NPC" },
      {
        name: "description",
        content: "Time reclaimed from scrolling, new activities, places visited and how you play.",
      },
      { property: "og:title", content: "My Stats — NPC" },
      {
        property: "og:description",
        content: "Time reclaimed from scrolling, new activities, places visited and how you play.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Page,
});

function Page() {
  return (
    <AppShell>
      <Analytics />
    </AppShell>
  );
}
