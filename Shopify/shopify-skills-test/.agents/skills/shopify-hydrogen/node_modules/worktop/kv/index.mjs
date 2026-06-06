// src/kv.ts
function f(a) {
  var s = (e, t) => `${e}__${t}`;
  return {
    get(e, t, r) {
      return l(a, s(e, t), r);
    },
    put(e, t, r, n) {
      return d(a, s(e, t), r, {toJSON: !0, ...n});
    },
    del(e, t) {
      return u(a, s(e, t));
    }
  };
}
function l(a, s, e = "json") {
  return typeof e == "string" || !e.metadata ? a.get(s, e) : a.getWithMetadata(s, e);
}
function d(a, s, e, t) {
  let n = !(t && !!t.toJSON) && typeof e == "string" || e instanceof ArrayBuffer || e instanceof ReadableStream ? e : JSON.stringify(e);
  return a.put(s, n, t).then(() => !0, () => !1);
}
function u(a, s) {
  return a.delete(s).then(() => !0, () => !1);
}
async function* K(a, s) {
  let {prefix: e, limit: t, cursor: r, metadata: n} = s || {};
  for (; ; ) {
    let o = await a.list({prefix: e, limit: t, cursor: r});
    if (r = o.cursor, yield {
      done: o.list_complete,
      keys: n ? o.keys : o.keys.map((i) => i.name)
    }, o.list_complete)
      return;
  }
}
async function M(a, s) {
  let {prefix: e, metadata: t = !1, limit: r = 50, page: n = 1} = s || {}, o = K(a, {prefix: e, limit: r, metadata: t});
  for await (let i of o) {
    if (--n && i.done)
      return [];
    if (n === 0)
      return i.keys;
  }
  return [];
}
async function m(a, s) {
  let e, t = "";
  for (; ; )
    if (e = await s(t = a()), e == null)
      return t;
}
export {
  f as Database,
  K as list,
  M as paginate,
  l as read,
  u as remove,
  m as until,
  d as write
};
