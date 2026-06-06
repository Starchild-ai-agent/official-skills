"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const React = require("react");
const CartLineContext = React.createContext(null);
function useCartLine() {
  const context = React.useContext(CartLineContext);
  if (context == null) {
    throw new Error("Expected a cart line context but none was found");
  }
  return context;
}
function CartLineProvider({
  children,
  line
}) {
  return /* @__PURE__ */ jsxRuntime.jsx(CartLineContext.Provider, { value: line, children });
}
exports.CartLineContext = CartLineContext;
exports.CartLineProvider = CartLineProvider;
exports.useCartLine = useCartLine;
//# sourceMappingURL=CartLineProvider.js.map
