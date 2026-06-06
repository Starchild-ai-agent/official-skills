// src/response.ts
import {byteLength as b} from "worktop/utils";

// src/internal/constants.ts
var s = "content-type", i = "content-length";

// src/response.ts
function h(u) {
  var e = this, r = e.headers = new Headers({
    "Cache-Control": "private, no-cache"
  });
  return e.body = "", e.finished = !1, e.status = e.statusCode = 200, e.getHeaders = () => Object.fromEntries(r), e.getHeaderNames = () => [...r.keys()], e.hasHeader = r.has.bind(r), e.getHeader = r.get.bind(r), e.removeHeader = r.delete.bind(r), e.setHeader = r.set.bind(r), Object.defineProperty(e, "status", {
    set: (n) => {
      e.statusCode = n;
    },
    get: () => e.statusCode
  }), e.end = (n) => {
    e.finished || (e.finished = !0, e.body = n);
  }, e.writeHead = (n, t) => {
    e.statusCode = n;
    for (let d in t)
      r.set(d, t[d]);
  }, e.send = (n, t, d) => {
    let a = typeof t, o = {};
    for (let p in d)
      o[p.toLowerCase()] = d[p];
    let f = o[i] || e.getHeader(i), l = o[s] || e.getHeader(s);
    t == null ? t = "" : a === "object" ? (t = JSON.stringify(t), l = l || "application/json;charset=utf-8") : a !== "string" && (t = String(t)), o[s] = l || "text/plain", o[i] = f || String(t.byteLength || b(t)), n === 204 || n === 205 || n === 304 ? (e.removeHeader(i), e.removeHeader(s), delete o[i], delete o[s], t = null) : u === "HEAD" && (t = null), e.writeHead(n, o), e.end(t);
  }, e;
}
export {
  h as ServerResponse
};
