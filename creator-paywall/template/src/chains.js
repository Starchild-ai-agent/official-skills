// chains.js — viem clients + plan helpers. One public client per chain, lazily created.
import { createPublicClient, http, parseUnits } from "viem";
import { CHAINS, PLANS } from "../config.js";

const clients = {};
export function client(chainId) {
  if (!CHAINS[chainId]) throw new Error(`Unsupported chainId ${chainId}`);
  if (!clients[chainId]) {
    clients[chainId] = createPublicClient({ transport: http(CHAINS[chainId].rpc) });
  }
  return clients[chainId];
}

// Find a plan by (chainId, token). token is "native" or a contract address.
export function findPlan(chainId, token) {
  const t = String(token).toLowerCase();
  return (
    PLANS.find(
      (p) => p.chainId === Number(chainId) && p.token.toLowerCase() === t
    ) || null
  );
}

// Price (human) for a plan + period -> base units (bigint as string).
export function expectedAmountWei(plan, period) {
  const price = period === "yearly" ? plan.price_yearly : plan.price_monthly;
  if (price == null) throw new Error(`Period ${period} not offered for ${plan.symbol}`);
  return parseUnits(String(price), plan.decimals).toString();
}

export function periodSeconds(period) {
  return period === "yearly" ? 365 * 24 * 3600 : 30 * 24 * 3600;
}

// Public, client-safe view of plans (no secrets).
export function publicPlans() {
  return PLANS.map((p) => ({
    chainId: p.chainId,
    chainName: CHAINS[p.chainId]?.name,
    symbol: p.symbol,
    token: p.token,
    decimals: p.decimals,
    price_monthly: p.price_monthly,
    price_yearly: p.price_yearly,
  }));
}
