// src/cache.ts
var s = caches.default;
async function a(t, e) {
  let n = e || t.request, o = typeof n != "string" && n.method === "HEAD";
  o && (n = new Request(n, {method: "GET"}));
  let r = await s.match(n);
  return o && r && (r = new Response(null, r)), r;
}
function c(t, e, n) {
  let o = n || t.request;
  return (typeof o == "string" || o.method === "GET") && i(e) && (e.headers.has("Set-Cookie") && (e = new Response(e.body, e), e.headers.append("Cache-Control", "private=Set-Cookie")), t.waitUntil(s.put(o, e.clone()))), e;
}
function i(t) {
  if (t.status === 206 || ~(t.headers.get("Vary") || "").indexOf("*"))
    return !1;
  let n = t.headers.get("Cache-Control") || "";
  return !/(private|no-cache|no-store)/i.test(n);
}
function p(t) {
  return (e, n) => e.respondWith(a(e, n).then((o) => o || t(e).then((r) => c(e, r, n))));
}
function l(t) {
  addEventListener("fetch", p(t));
}
export {
  s as Cache,
  i as isCacheable,
  l as listen,
  a as lookup,
  p as reply,
  c as save
};
