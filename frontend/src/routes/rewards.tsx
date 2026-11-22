import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Rewards } from "@/pages/Rewards";

export const Route = createFileRoute("/rewards")({
  head: () => ({
    meta: [
      { title: "Perks & Rewards — NPC" },
      { name: "description", content: "Redeem your earned adventure XP for Raju Idli discounts, Starbucks, McDonald's, and Amazon vouchers." },
      { property: "og:title", content: "Perks & Rewards — NPC" },
      { property: "og:description", content: "Redeem your earned adventure XP for Raju Idli discounts, Starbucks, McDonald's, and Amazon vouchers." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Page,
});

function Page() {
  return (
    <AppShell>
      <Rewards />
    </AppShell>
  );
}
