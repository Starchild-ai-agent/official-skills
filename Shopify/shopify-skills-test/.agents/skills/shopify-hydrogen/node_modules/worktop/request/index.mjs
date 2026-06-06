// src/internal/request.ts
function n(e) {
  let r, t, a, o = {};
  for ([r, t] of e)
    o[r] = (a = o[r]) !== void 0 ? [].concat(a, t) : t;
  return o;
}
async function i(e, r) {
  if (!(!e.body || !r))
    return ~r.indexOf("application/json") ? e.json() : ~r.indexOf("multipart/form-data") || ~r.indexOf("application/x-www-form-urlencoded") ? e.formData().then(n) : ~r.indexOf("text/") ? e.text() : e.arrayBuffer();
}

// src/request.ts
function f(e) {
  let r = this, {request: t} = e, a = new URL(t.url);
  return r.url = t.url, r.method = t.method, r.headers = t.headers, r.extend = e.waitUntil.bind(e), r.cf = t.cf, r.params = {}, r.path = a.pathname, r.hostname = a.hostname, r.origin = a.origin, r.query = a.searchParams, r.search = a.search, r.body = i.bind(0, t, r.headers.get("content-type")), r.body.blob = t.blob.bind(t), r.body.text = t.text.bind(t), r.body.arrayBuffer = t.arrayBuffer.bind(t), r.body.formData = t.formData.bind(t), r.body.json = t.json.bind(t), r;
}
export {
  f as ServerRequest
};
