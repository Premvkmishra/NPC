import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Reward, RewardRedemption } from "@/lib/types";
import { Btn } from "@/components/Btn";
import { PixelIcon } from "@/components/PixelIcon";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";

export function Rewards() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"catalog" | "vouchers">("catalog");
  const [filterCat, setFilterCat] = useState<string>("all");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [redeemedVoucher, setRedeemedVoucher] = useState<RewardRedemption | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["rewards"],
    queryFn: () => api.listRewards(),
  });

  const redeemMutation = useMutation({
    mutationFn: (rewardId: string) => api.redeemReward(rewardId),
    onSuccess: (res) => {
      setRedeemedVoucher(res.redemption);
      qc.invalidateQueries({ queryKey: ["rewards"] });
      qc.invalidateQueries({ queryKey: ["home"] });
      qc.invalidateQueries({ queryKey: ["journey"] });
    },
  });

  const copyCode = (code: string) => {
    navigator.clipboard?.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2500);
  };

  if (isLoading) return <LoadingState label="Loading Rewards Hub…" />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} />;

  const rewards = data?.rewards ?? [];
  const redemptions = data?.redemptions ?? [];
  const playerXp = data?.player_xp ?? 0;

  const filteredRewards = filterCat === "all"
    ? rewards
    : rewards.filter((r) => r.category === filterCat);

  return (
    <div className="space-y-5">
      {/* XP Balance HUD Banner */}
      <section className="ink-border bg-card p-4 shadow-hard">
        <div className="flex items-center justify-between">
          <div>
            <p className="hud-label text-muted-foreground">Spendable Adventure XP</p>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="font-pixel text-4xl leading-none text-ink">{playerXp}</span>
              <span className="font-mono text-sm font-bold text-muted-foreground">XP</span>
            </div>
          </div>
          <div className="ink-border bg-butter px-3 py-1.5 text-center shadow-hard-sm">
            <span className="hud-label block text-[10px]">Perks Claimed</span>
            <span className="font-mono text-xl font-bold">{redemptions.length}</span>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground font-mono">
          Convert side quest XP into real food discounts & gift cards.
        </p>
      </section>

      {/* Main Mode Toggle: Rewards Catalog vs My Vouchers */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setActiveTab("catalog")}
          className={`flex-1 min-h-11 ink-border font-pixel text-sm uppercase tracking-wider transition-all ${
            activeTab === "catalog"
              ? "bg-lime translate-x-0.5 translate-y-0.5"
              : "bg-card shadow-hard-sm"
          }`}
        >
          🎁 Available Perks
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("vouchers")}
          className={`flex-1 min-h-11 ink-border font-pixel text-sm uppercase tracking-wider transition-all relative ${
            activeTab === "vouchers"
              ? "bg-butter translate-x-0.5 translate-y-0.5"
              : "bg-card shadow-hard-sm"
          }`}
        >
          🎟️ My Vouchers {redemptions.length > 0 && `(${redemptions.length})`}
        </button>
      </div>

      {/* SUCCESS MODAL / POPUP */}
      {redeemedVoucher && (
        <div className="ink-border bg-lime p-4 shadow-hard space-y-3 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between">
            <span className="font-pixel text-xl uppercase">🎉 Perk Unlocked!</span>
            <button
              onClick={() => setRedeemedVoucher(null)}
              className="ink-border bg-card px-2 py-0.5 text-xs font-mono font-bold"
            >
              ✕
            </button>
          </div>
          <p className="text-sm font-semibold">{redeemedVoucher.reward_title}</p>
          <div className="ink-border bg-card p-3 text-center space-y-1">
            <p className="hud-label text-muted-foreground">Your Voucher Code</p>
            <p className="font-mono text-xl font-black tracking-widest text-ink select-all">
              {redeemedVoucher.voucher_code}
            </p>
          </div>
          <div className="flex gap-2">
            <Btn
              variant="ink"
              className="flex-1 text-xs"
              onClick={() => copyCode(redeemedVoucher.voucher_code)}
            >
              {copiedCode === redeemedVoucher.voucher_code ? "✓ Copied Code!" : "Copy Voucher Code"}
            </Btn>
            <Btn
              variant="paper"
              className="text-xs"
              onClick={() => {
                setRedeemedVoucher(null);
                setActiveTab("vouchers");
              }}
            >
              View in My Vouchers
            </Btn>
          </div>
        </div>
      )}

      {/* CATALOG VIEW */}
      {activeTab === "catalog" && (
        <div className="space-y-4">
          {/* Category Filter Pills */}
          <div className="flex gap-1.5 overflow-x-auto pb-1 text-xs">
            {[
              { id: "all", label: "All Perks" },
              { id: "food", label: "🍔 Local Idli & Food" },
              { id: "lifestyle", label: "☕ Starbucks & Cafes" },
              { id: "shopping", label: "📦 Amazon Pay" },
            ].map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setFilterCat(c.id)}
                className={`whitespace-nowrap px-3 py-1.5 ink-border font-pixel uppercase ${
                  filterCat === c.id ? "bg-ink text-paper" : "bg-card shadow-hard-sm"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* Reward Cards */}
          <div className="space-y-3">
            {filteredRewards.map((r: Reward) => {
              const canAfford = playerXp >= r.cost_xp;
              const isPendingThis = redeemMutation.isPending && (redeemMutation.variables as string) === r.id;

              return (
                <article
                  key={r.id}
                  className="ink-border bg-card p-4 shadow-hard space-y-3 relative overflow-hidden"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="ink-border bg-orange px-2 py-0.5 font-pixel text-[11px] uppercase tracking-wider text-ink font-bold">
                          ₹{r.discount_amount_inr} OFF
                        </span>
                        <span className="font-mono text-xs font-semibold text-muted-foreground">
                          {r.brand}
                        </span>
                      </div>
                      <h3 className="font-pixel text-lg leading-tight mt-1">{r.title}</h3>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-mono text-sm font-bold block ink-border bg-card px-2 py-0.5">
                        {r.cost_xp} XP
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {r.description}
                  </p>

                  {r.location && (
                    <p className="text-[11px] font-mono text-ink flex items-center gap-1 bg-paper/60 p-1.5 ink-border">
                      <PixelIcon name="pin" size={14} />
                      <span>{r.location}</span>
                    </p>
                  )}

                  {r.terms && (
                    <p className="text-[10px] font-mono text-muted-foreground">
                      * {r.terms}
                    </p>
                  )}

                  <Btn
                    className="w-full text-sm"
                    variant={canAfford ? "primary" : "paper"}
                    disabled={!canAfford || redeemMutation.isPending}
                    onClick={() => redeemMutation.mutate(r.id)}
                  >
                    {isPendingThis
                      ? "Generating Voucher…"
                      : canAfford
                      ? `Redeem for ${r.cost_xp} XP`
                      : `Need ${r.cost_xp - playerXp} more XP`}
                  </Btn>
                </article>
              );
            })}
          </div>

          {redeemMutation.isError && (
            <ErrorState error={redeemMutation.error} />
          )}
        </div>
      )}

      {/* MY CLAIMED VOUCHERS VIEW */}
      {activeTab === "vouchers" && (
        <div className="space-y-3">
          {redemptions.length === 0 ? (
            <EmptyState text="You haven't redeemed any vouchers yet. Complete today's side quest to earn XP!" />
          ) : (
            redemptions.map((red) => {
              const isCopied = copiedCode === red.voucher_code;
              const expiryDate = new Date(red.expires_at).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              });

              return (
                <div
                  key={red.id}
                  className="ink-border bg-card p-4 shadow-hard space-y-3 border-dashed relative"
                >
                  <div className="flex items-center justify-between border-b pb-2 border-ink/20">
                    <div>
                      <span className="hud-label text-muted-foreground">{red.brand}</span>
                      <h4 className="font-pixel text-base">{red.reward_title}</h4>
                    </div>
                    <span className="ink-border bg-lime px-2 py-0.5 text-[10px] font-mono uppercase font-bold">
                      ACTIVE
                    </span>
                  </div>

                  <div className="ink-border bg-paper p-3 text-center space-y-1">
                    <p className="hud-label text-[10px] text-muted-foreground">VOUCHER CODE</p>
                    <p className="font-mono text-lg font-black tracking-widest text-ink select-all">
                      {red.voucher_code}
                    </p>
                  </div>

                  {/* Simulated Ticket Barcode */}
                  <div className="flex justify-center gap-1 opacity-70 py-1">
                    {[1, 2, 4, 2, 1, 3, 1, 2, 4, 3, 1, 2, 3, 2, 1, 4, 2, 3, 1].map((w, i) => (
                      <div
                        key={i}
                        className="bg-ink h-6"
                        style={{ width: `${w * 2}px` }}
                      />
                    ))}
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground pt-1">
                    <span>Valid until: {expiryDate}</span>
                    <Btn
                      variant="ink"
                      className="text-xs px-3 py-1 min-h-8"
                      onClick={() => copyCode(red.voucher_code)}
                    >
                      {isCopied ? "✓ Copied" : "Copy Code"}
                    </Btn>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
