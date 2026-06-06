// src/router.ts
import {parse as f} from "regexparam";
import {ServerRequest as u} from "worktop/request";
import {ServerResponse as R} from "worktop/response";

// src/internal/constants.ts
var c = {
  "400": "Bad Request",
  "401": "Unauthorized",
  "403": "Forbidden",
  "404": "Not Found",
  "405": "Method Not Allowed",
  "406": "Not Acceptable",
  "409": "Conflict",
  "410": "Gone",
  "411": "Length Required",
  "413": "Payload Too Large",
  "422": "Unprocessable Entity",
  "426": "Upgrade Required",
  "428": "Precondition Required",
  "429": "Too Many Requests",
  "500": "Internal Server Error",
  "501": "Not Implemented",
  "502": "Bad Gateway",
  "503": "Service Unavailable",
  "504": "Gateway Timeout"
};

// src/router.ts
function m(t) {
  return (o) => o.respondWith(t(o));
}
function w(t) {
  addEventListener("fetch", m(t));
}
var l = !1;
function E(...t) {
  return async function(o, s) {
    let r, e, n = t.length;
    for (r of t)
      if (e = await d(r, --n <= 0 && !l, o, s))
        return e;
  };
}
async function d(t, o, s, r, ...e) {
  let n = await t(s, r, ...e);
  if (n instanceof Response)
    return n;
  if (o || r.finished)
    return new Response(r.body, r);
}
function y(t, o, s) {
  let r = {}, e, n, a, i, p;
  if (n = t[o]) {
    if (e = n.__s[s])
      return {params: r, handler: e.handler};
    for ([a, i] of n.__d)
      if (p = a.exec(s), p !== null) {
        if (p.groups !== void 0)
          for (e in p.groups)
            r[e] = p.groups[e];
        else if (i.keys.length > 0)
          for (e = 0; e < i.keys.length; )
            r[i.keys[e++]] = p[e];
        return {params: r, handler: i.handler};
      }
  }
}
function x() {
  let t, o = {};
  return t = {
    add(s, r, e) {
      let n = o[s];
      if (n === void 0 && (n = o[s] = {
        __d: new Map(),
        __s: {}
      }), r instanceof RegExp)
        n.__d.set(r, {keys: [], handler: e});
      else if (/[:|*]/.test(r)) {
        let {keys: a, pattern: i} = f(r);
        n.__d.set(i, {keys: a, handler: e});
      } else
        n.__s[r] = {keys: [], handler: e};
    },
    onerror(s, r, e, n) {
      let a = c[e = e || 500], i = n && n.message || a || String(e);
      return new Response(i, {status: e, statusText: a});
    },
    async run(s) {
      let r, e = new u(s), n = new R(e.method);
      if (l = !!t.prepare) {
        if (r = await d(t.prepare, !1, e, n), r)
          return r;
        l = !1;
      }
      return r = y(o, e.method, e.path), r ? (e.params = r.params, d(r.handler, !0, e, n).catch((a) => d(t.onerror, !0, e, n, 500, a))) : d(t.onerror, !0, e, n, 404);
    }
  };
}
export {
  x as Router,
  c as STATUS_CODES,
  E as compose,
  w as listen,
  m as reply
};
