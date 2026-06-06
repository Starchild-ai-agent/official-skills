import { jsx } from "react/jsx-runtime";
import { useCartLine } from "./CartLineProvider.mjs";
function CartLineQuantity(props) {
  const cartLine = useCartLine();
  const { as, ...passthroughProps } = props;
  const Wrapper = as ? as : "span";
  return /* @__PURE__ */ jsx(Wrapper, { ...passthroughProps, children: cartLine.quantity });
}
export {
  CartLineQuantity
};
//# sourceMappingURL=CartLineQuantity.mjs.map
