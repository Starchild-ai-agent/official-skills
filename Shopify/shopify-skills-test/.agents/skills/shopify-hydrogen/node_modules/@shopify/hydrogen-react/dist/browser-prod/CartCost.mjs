import { jsx } from "react/jsx-runtime";
import { Money } from "./Money.mjs";
import { useCart } from "./CartProvider.mjs";
function CartCost(props) {
  const { cost } = useCart();
  const { amountType = "total", children, ...passthroughProps } = props;
  let amount;
  if (amountType == "total") {
    amount = cost == null ? void 0 : cost.totalAmount;
  } else if (amountType == "subtotal") {
    amount = cost == null ? void 0 : cost.subtotalAmount;
  } else if (amountType == "tax") {
    amount = cost == null ? void 0 : cost.totalTaxAmount;
  } else if (amountType == "duty") {
    amount = cost == null ? void 0 : cost.totalDutyAmount;
  }
  if (amount == null) {
    return null;
  }
  return /* @__PURE__ */ jsx(Money, { ...passthroughProps, data: amount, children });
}
export {
  CartCost
};
//# sourceMappingURL=CartCost.mjs.map
