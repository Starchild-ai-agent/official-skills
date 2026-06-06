// src/base64.ts
var o = btoa, r = atob;
function c(e) {
  return btoa(e).replace(/\+/g, "-").replace(/\//g, "_").replace(/\=/g, "");
}
export {
  c as base64url,
  r as decode,
  o as encode
};
