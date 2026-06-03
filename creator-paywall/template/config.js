// ============================================================================
// config.js — the ONLY file most creators need to edit.
// Define which chains/tokens you accept and your subscription prices.
// ============================================================================

// Public RPCs (no API key). Swap for your own (Alchemy/QuickNode) in production.
export const CHAINS = {
  1: {
    name: "Ethereum",
    rpc: process.env.RPC_ETHEREUM || "https://eth.llamarpc.com",
    nativeSymbol: "ETH",
    explorer: "https://etherscan.io",
    confirmations: 2,
  },
  8453: {
    name: "Base",
    rpc: process.env.RPC_BASE || "https://mainnet.base.org",
    nativeSymbol: "ETH",
    explorer: "https://basescan.org",
    confirmations: 3,
  },
  56: {
    name: "BSC",
    rpc: process.env.RPC_BSC || "https://bsc-dataseed.binance.org",
    nativeSymbol: "BNB",
    explorer: "https://bscscan.com",
    confirmations: 3,
  },
};

// The wallet that RECEIVES payments = your Starchild agent wallet address.
// Get it via the wallet skill: wallet_info -> evm address. Paste it here or set CREATOR_WALLET in .env.
export const CREATOR_WALLET = (process.env.CREATOR_WALLET || "0xYOUR_AGENT_WALLET_ADDRESS").toLowerCase();

// ----------------------------------------------------------------------------
// Accepted payment options. Each entry = one (chain, token, price) the user can pick.
//  - token "native" means the chain's native coin (ETH / BNB).
//  - For ERC20 / custom tokens, give the contract address. `decimals` is REQUIRED
//    (read it once from the token contract; e.g. USDC=6, most ERC20=18).
//  - price_monthly / price_yearly are HUMAN amounts (e.g. 5 = 5 USDC). Set to null to disable a period.
// ----------------------------------------------------------------------------
export const PLANS = [
  // --- Stablecoins (recommended: stable price) ---
  {
    chainId: 8453,
    symbol: "USDC",
    token: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", // USDC on Base
    decimals: 6,
    price_monthly: 5,
    price_yearly: 50,
  },
  {
    chainId: 56,
    symbol: "USDT",
    token: "0x55d398326f99059fF775485246999027B3197955", // USDT on BSC
    decimals: 18,
    price_monthly: 5,
    price_yearly: 50,
  },
  // --- Native coin example ---
  {
    chainId: 8453,
    symbol: "ETH",
    token: "native",
    decimals: 18,
    price_monthly: 0.002,
    price_yearly: 0.02,
  },
  // --- Custom token example (a creator's own token) ---
  // {
  //   chainId: 1,
  //   symbol: "MYTOKEN",
  //   token: "0xYourTokenContract...",
  //   decimals: 18,
  //   price_monthly: 1000,
  //   price_yearly: 10000,
  // },
];

// SIWE domain shown to users when they sign in. Set to your real domain in prod.
export const SIWE_DOMAIN = process.env.SIWE_DOMAIN || "localhost";
export const SIWE_STATEMENT = "Sign in to access your subscription.";

// JWT secret for sessions. MUST be set in .env for production.
export const JWT_SECRET = process.env.JWT_SECRET || "dev-insecure-secret-change-me";
export const SESSION_TTL_HOURS = 24 * 7; // session validity (re-sign after this)

// How far back (in blocks) the "Check payment" button scans for a matching transfer.
// Kept small to avoid heavy public-RPC calls. We anchor the scan at the block when the
// user created the payment intent, so the range stays tiny in normal use.
export const SCAN_MAX_BLOCKS = {
  1: 7200,     // ~1 day on Ethereum
  8453: 43200, // ~1 day on Base (2s blocks)
  56: 28800,   // ~1 day on BSC (3s blocks)
};
