// src/crypto.ts
import {encode as n, toHEX as p} from "worktop/utils";
function i(e, t) {
  return crypto.subtle.digest(e, n(t)).then(p);
}
var f = /* @__PURE__ */ i.bind(0, "SHA-1"), m = /* @__PURE__ */ i.bind(0, "SHA-256"), c = /* @__PURE__ */ i.bind(0, "SHA-384"), A = /* @__PURE__ */ i.bind(0, "SHA-512");
function u(e, t, r) {
  return crypto.subtle.importKey("raw", n(t), e, !1, r);
}
function b(e, t, r = !1) {
  return crypto.subtle.generateKey(e, r, t);
}
function d(e, t, r) {
  return crypto.subtle.sign(e, t, n(r));
}
function h(e, t, r, o) {
  return crypto.subtle.verify(e, t, o, n(r));
}
function K(e, t) {
  if (e.byteLength !== t.byteLength)
    return !1;
  let r = e.length, o = !1;
  for (; r-- > 0; )
    e[r] !== t[r] && (o = !0);
  return !o;
}
async function x(e, t, r, o, s) {
  let y = await u("PBKDF2", t, ["deriveBits"]), g = {
    name: "PBKDF2",
    salt: n(r),
    iterations: o,
    hash: e
  };
  return crypto.subtle.deriveBits(g, y, s << 3);
}
export {
  x as PBKDF2,
  f as SHA1,
  m as SHA256,
  c as SHA384,
  A as SHA512,
  i as digest,
  b as keygen,
  u as keyload,
  d as sign,
  K as timingSafeEqual,
  h as verify
};
