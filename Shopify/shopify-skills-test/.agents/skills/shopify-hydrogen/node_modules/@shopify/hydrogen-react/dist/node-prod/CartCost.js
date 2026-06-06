"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const Money = require("./Money.js");
const CartProvider = require("./CartProvider.js");
function CartCost(props) {
  const { cost } = CartProvider.useCart();
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
  return /* @__PURE__ */ jsxRuntime.jsx(Money.Money, { ...passthroughProps, data: amount, children });
}
exports.CartCost = CartCost;
//# sourceMappingURL=CartCost.js.map
