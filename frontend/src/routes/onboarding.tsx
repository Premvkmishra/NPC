import { createFileRoute } from "@tanstack/react-router";
import { Onboarding } from "@/pages/Onboarding";

export const Route = createFileRoute("/onboarding")({
  head: () => ({ meta: [
    { title: "Start Your Save File — NPC" }, { name: "description", content: "Tell NPC what you like and get personalised real-world side quests." },
    { property: "og:title", content: "Start Your Save File — NPC" }, { property: "og:description", content: "Tell NPC what you like and get personalised real-world side quests." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Page,
});

function Page() {
  return <div className="mx-auto min-h-screen w-full max-w-[430px] paper-bg px-4 py-6 md:my-6 md:min-h-[calc(100vh-3rem)] md:ink-border md:border-paper"><Onboarding /></div>;
}
