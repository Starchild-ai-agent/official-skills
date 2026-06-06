"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const React = require("react");
const CartProvider = require("./CartProvider.js");
const BaseButton = require("./BaseButton.js");
function CartCheckoutButton(props) {
  const [requestedCheckout, setRequestedCheckout] = React.useState(false);
  const { status, checkoutUrl } = CartProvider.useCart();
  const { children, ...passthroughProps } = props;
  React.useEffect(() => {
    if (requestedCheckout && checkoutUrl && status === "idle") {
      window.location.href = checkoutUrl;
    }
  }, [requestedCheckout, status, checkoutUrl]);
  return /* @__PURE__ */ jsxRuntime.jsx(
    BaseButton.BaseButton,
    {
      ...passthroughProps,
      disabled: requestedCheckout || passthroughProps.disabled,
      onClick: () => setRequestedCheckout(true),
      children
    }
  );
}
exports.CartCheckoutButton = CartCheckoutButton;
//# sourceMappingURL=CartCheckoutButton.js.map
