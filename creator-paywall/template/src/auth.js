// auth.js — SIWE (Sign-In With Ethereum). Wallet address IS the identity.
import { createSiweMessage, verifySiweMessage } from "viem/siwe";
import jwt from "jsonwebtoken";
import { client } from "./chains.js";
import { SIWE_DOMAIN, SIWE_STATEMENT, JWT_SECRET, SESSION_TTL_HOURS } from "../config.js";
import { saveNonce, takeNonce, getSubscription, now } from "./db.js";

const randomNonce = () =>
  [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");

// Build the exact SIWE message the client must sign. We send it ready-made so
// the signed message and the server-verified message are byte-identical.
export function buildLoginMessage({ address, chainId, uri }) {
  const nonce = randomNonce();
  saveNonce(address, nonce);
  const message = createSiweMessage({
    domain: SIWE_DOMAIN,
    address,
    statement: SIWE_STATEMENT,
    uri: uri || `http://${SIWE_DOMAIN}`,
    version: "1",
    chainId: Number(chainId) || 1,
    nonce,
  });
  return message;
}

// Verify the signed message, consume the nonce, issue a session JWT.
export async function login({ message, signature, chainId }) {
  // pull address + nonce out of the message to validate the nonce we issued
  const addrMatch = message.match(/\n(0x[0-9a-fA-F]{40})\n/);
  const nonceMatch = message.match(/Nonce: (\w+)/);
  if (!addrMatch || !nonceMatch) throw new Error("malformed SIWE message");
  const address = addrMatch[1];
  const expected = takeNonce(address);
  if (!expected || expected !== nonceMatch[1]) throw new Error("invalid or expired nonce");

  const valid = await verifySiweMessage(client(Number(chainId) || 1), { message, signature });
  if (!valid) throw new Error("signature verification failed");

  const token = jwt.sign({ sub: address.toLowerCase() }, JWT_SECRET, {
    expiresIn: `${SESSION_TTL_HOURS}h`,
  });
  return { token, address: address.toLowerCase() };
}

export function verifySession(token) {
  try {
    return jwt.verify(token, JWT_SECRET).sub;
  } catch {
    return null;
  }
}

// Express middleware: attaches req.wallet if logged in.
export function requireAuth(req, res, next) {
  const token = req.cookies?.session || (req.headers.authorization || "").replace("Bearer ", "");
  const wallet = token && verifySession(token);
  if (!wallet) return res.status(401).json({ error: "not authenticated" });
  req.wallet = wallet;
  next();
}

// Express middleware: requires an active (non-expired) subscription.
export function requireSubscription(req, res, next) {
  const sub = getSubscription(req.wallet);
  if (!sub || sub.expires_at <= now())
    return res.status(402).json({ error: "subscription required", subscribed: false });
  req.subscription = sub;
  next();
}
