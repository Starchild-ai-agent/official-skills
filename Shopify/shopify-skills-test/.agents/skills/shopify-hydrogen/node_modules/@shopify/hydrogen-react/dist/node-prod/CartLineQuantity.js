"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const CartLineProvider = require("./CartLineProvider.js");
function CartLineQuantity(props) {
  const cartLine = CartLineProvider.useCartLine();
  const { as, ...passthroughProps } = props;
  const Wrapper = as ? as : "span";
  return /* @__PURE__ */ jsxRuntime.jsx(Wrapper, { ...passthroughProps, children: cartLine.quantity });
}
exports.CartLineQuantity = CartLineQuantity;
//# sourceMappingURL=CartLineQuantity.js.map
