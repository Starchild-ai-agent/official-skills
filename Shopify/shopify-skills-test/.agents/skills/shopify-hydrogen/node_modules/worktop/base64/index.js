// src/base64.ts
var o = btoa, r = atob;
function c(e) {
  return btoa(e).replace(/\+/g, "-").replace(/\//g, "_").replace(/\=/g, "");
}


exports.base64url = c;
exports.decode = r;
exports.encode = o;