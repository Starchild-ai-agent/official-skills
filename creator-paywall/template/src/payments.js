// payments.js — the heart of the paywall: verify an on-chain transfer matches an intent.
//
// Matching rules (all must hold):
//   1. tx confirmed (>= configured confirmations) and successful
//   2. recipient == CREATOR_WALLET
//   3. sender   == the logged-in user's wallet   <-- this is the identity = payer link
//   4. token matches the chosen plan
//   5. transferred amount >= expected price
//   6. txHash not already consumed (idempotent)
import { getAddress, parseAbiItem } from "viem";
import { CREATOR_WALLET, CHAINS, SCAN_MAX_BLOCKS } from "../config.js";
import { client } from "./chains.js";

const TRANSFER_EVENT = parseAbiItem(
  "event Transfer(address indexed from, address indexed to, uint256 value)"
);

const eqAddr = (a, b) => String(a).toLowerCase() === String(b).toLowerCase();

// Verify a specific txHash against an intent. Returns { ok, reason?, amount }.
export async function verifyTxHash({ chainId, token, expectedWei, wallet, txHash }) {
  const c = client(chainId);
  const conf = CHAINS[chainId].confirmations;

  let receipt;
  try {
    receipt = await c.getTransactionReceipt({ hash: txHash });
  } catch {
    return { ok: false, reason: "tx not found yet — wait for it to be mined" };
  }
  if (receipt.status !== "success") return { ok: false, reason: "tx failed on-chain" };

  const latest = await c.getBlockNumber();
  const confirmations = Number(latest - receipt.blockNumber) + 1;
  if (confirmations < conf)
    return { ok: false, reason: `waiting for confirmations (${confirmations}/${conf})` };

  if (token === "native") {
    const tx = await c.getTransaction({ hash: txHash });
    if (!eqAddr(tx.from, wallet)) return { ok: false, reason: "sender is not your wallet" };
    if (!tx.to || !eqAddr(tx.to, CREATOR_WALLET))
      return { ok: false, reason: "recipient is not the creator wallet" };
    if (tx.value < BigInt(expectedWei))
      return { ok: false, reason: "amount below required price" };
    return { ok: true, amount: tx.value.toString() };
  }

  // ERC20: find a matching Transfer log emitted by the token contract.
  for (const log of receipt.logs) {
    if (!eqAddr(log.address, token)) continue;
    try {
      const decoded = decodeTransfer(log);
      if (!decoded) continue;
      if (!eqAddr(decoded.from, wallet)) continue;
      if (!eqAddr(decoded.to, CREATOR_WALLET)) continue;
      if (decoded.value < BigInt(expectedWei)) continue;
      return { ok: true, amount: decoded.value.toString() };
    } catch {
      continue;
    }
  }
  return { ok: false, reason: "no matching token transfer found in this tx" };
}

function decodeTransfer(log) {
  // Transfer(address,address,uint256): topic0 = sig, topic1 = from, topic2 = to, data = value
  const sig = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
  if (log.topics[0]?.toLowerCase() !== sig) return null;
  const from = "0x" + log.topics[1].slice(26);
  const to = "0x" + log.topics[2].slice(26);
  const value = BigInt(log.data);
  return { from: getAddress(from), to: getAddress(to), value };
}

// On-demand scan (the "Check payment" button) for ERC20 transfers from user -> creator.
// Anchored at intent.from_block so the range stays tiny. Returns txHash or null.
// NOTE: native-coin payments cannot be log-scanned — those must be confirmed via txHash.
export async function scanForPayment({ chainId, token, expectedWei, wallet, fromBlock }) {
  if (token === "native")
    return { found: false, reason: "native payments: submit the tx hash to confirm" };

  const c = client(chainId);
  const latest = await c.getBlockNumber();
  const maxSpan = BigInt(SCAN_MAX_BLOCKS[chainId] || 20000);
  let start = BigInt(fromBlock);
  if (latest - start > maxSpan) start = latest - maxSpan; // clamp

  const logs = await c.getLogs({
    address: token,
    event: TRANSFER_EVENT,
    args: { from: getAddress(wallet), to: getAddress(CREATOR_WALLET) },
    fromBlock: start,
    toBlock: latest,
  });

  for (const log of logs) {
    if (log.args.value >= BigInt(expectedWei)) {
      return { found: true, txHash: log.transactionHash, amount: log.args.value.toString() };
    }
  }
  return { found: false, reason: "no matching transfer found yet" };
}
