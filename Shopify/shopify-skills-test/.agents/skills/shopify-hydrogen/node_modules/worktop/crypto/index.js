// src/crypto.ts
const { encode:n, toHEX:p } = require('worktop/utils');
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


exports.PBKDF2 = x;
exports.SHA1 = f;
exports.SHA256 = m;
exports.SHA384 = c;
exports.SHA512 = A;
exports.digest = i;
exports.keygen = b;
exports.keyload = u;
exports.sign = d;
exports.timingSafeEqual = K;
exports.verify = h;