import { jsx } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { useCart } from "./CartProvider.mjs";
import { BaseButton } from "./BaseButton.mjs";
function CartCheckoutButton(props) {
  const [requestedCheckout, setRequestedCheckout] = useState(false);
  const { status, checkoutUrl } = useCart();
  const { children, ...passthroughProps } = props;
  useEffect(() => {
    if (requestedCheckout && checkoutUrl && status === "idle") {
      window.location.href = checkoutUrl;
    }
  }, [requestedCheckout, status, checkoutUrl]);
  return /* @__PURE__ */ jsx(
    BaseButton,
    {
      ...passthroughProps,
      disabled: requestedCheckout || passthroughProps.disabled,
      onClick: () => setRequestedCheckout(true),
      children
    }
  );
}
export {
  CartCheckoutButton
};
//# sourceMappingURL=CartCheckoutButton.mjs.map
