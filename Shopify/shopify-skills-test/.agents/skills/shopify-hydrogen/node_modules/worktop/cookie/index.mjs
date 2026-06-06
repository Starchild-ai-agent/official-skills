// src/cookie.ts
var g = new Set([
  "domain",
  "path",
  "max-age",
  "expires",
  "samesite",
  "secure",
  "httponly"
]);
function u(a) {
  let r = {}, e, t, n = 0, m = a.split(/;\s*/g), s, i;
  for (; n < m.length; n++)
    if (t = m[n], e = t.indexOf("="), ~e) {
      if (s = t.substring(0, e++).trim(), i = t.substring(e).trim(), i[0] === '"' && (i = i.substring(1, i.length - 1)), ~i.indexOf("%"))
        try {
          i = decodeURIComponent(i);
        } catch (f) {
        }
      g.has(t = s.toLowerCase()) ? t === "expires" ? r.expires = new Date(i) : t === "max-age" ? r.maxage = +i : r[t] = i : r[s] = i;
    } else
      (s = t.trim().toLowerCase()) && (s === "httponly" || s === "secure") && (r[s] = !0);
  return r;
}
function l(a, r, e = {}) {
  let t = a + "=" + encodeURIComponent(r);
  return e.expires && (t += "; Expires=" + new Date(e.expires).toUTCString()), e.maxage != null && e.maxage >= 0 && (t += "; Max-Age=" + (e.maxage | 0)), e.domain && (t += "; Domain=" + e.domain), e.path && (t += "; Path=" + e.path), e.samesite && (t += "; SameSite=" + e.samesite), (e.secure || e.samesite === "None") && (t += "; Secure"), e.httponly && (t += "; HttpOnly"), t;
}
export {
  u as parse,
  l as stringify
};
