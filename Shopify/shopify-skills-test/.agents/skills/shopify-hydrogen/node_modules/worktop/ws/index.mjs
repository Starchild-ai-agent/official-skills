// src/internal/ws.ts
import {STATUS_CODES as l} from "worktop";
import {byteLength as p} from "worktop/utils";
function r(t) {
  let e = l[t];
  return new Response(e, {
    status: t,
    statusText: e,
    headers: {
      Connection: "close",
      "Content-Type": "text/plain",
      "Content-Length": "" + p(e)
    }
  });
}

// src/ws.ts
function d(t) {
  if (t.method !== "GET")
    return r(405);
  let e = t.headers.get("upgrade");
  if (e !== "websocket")
    return r(426);
  if (e = (t.headers.get("sec-websocket-key") || "").trim(), !/^[+/0-9A-Za-z]{22}==$/.test(e))
    return r(400);
  if (e = t.headers.get("sec-websocket-version"), e !== "13")
    return r(400);
}
function v(t) {
  return function(e) {
    let o = d(e);
    if (o)
      return o;
    let {0: c, 1: n} = new WebSocketPair(), u = {};
    function a(s) {
      return t(e, {
        send: n.send.bind(n),
        close: n.close.bind(n),
        context: u,
        event: s
      });
    }
    async function i(s) {
      try {
        await a(s);
      } finally {
        n.close();
      }
    }
    return n.accept(), n.addEventListener("close", i), n.addEventListener("message", a), n.addEventListener("error", i), new Response(null, {
      status: 101,
      statusText: "Switching Protocols",
      webSocket: c
    });
  };
}
export {
  d as connect,
  v as listen
};
