// src/cors.ts
var a = {
  origin: "*",
  methods: ["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"],
  headers: [],
  expose: []
};
function l(o, t, s) {
  let e = t ? {...a, ...t} : a;
  o.setHeader("Access-Control-Allow-Origin", e.origin), e.origin !== "*" && o.headers.append("Vary", "Origin"), e.credentials && o.setHeader("Access-Control-Allow-Credentials", "true"), e.expose.length && o.setHeader("Access-Control-Expose-Headers", e.expose), s && (e.maxage != null && o.setHeader("Access-Control-Max-Age", e.maxage), e.methods.length && o.setHeader("Access-Control-Allow-Methods", e.methods), e.headers.length && o.setHeader("Access-Control-Allow-Headers", e.headers));
}
function g(o = {}) {
  let t = o.origin = o.origin || "*", s = typeof t == "string";
  return function(e, i) {
    let r, n = e.method === "OPTIONS";
    s || (r = e.headers.get("Origin") || "", o.origin = t === !0 && r || t instanceof RegExp && t.test(r) && r || "false"), l(i, o, n), n && (o.headers || (r = e.headers.get("Access-Control-Request-Headers"), r && i.setHeader("Access-Control-Allow-Headers", r), i.headers.append("Vary", "Access-Control-Request-Headers")), i.statusCode = 204, i.end(null));
  };
}
export {
  a as config,
  l as headers,
  g as preflight
};
