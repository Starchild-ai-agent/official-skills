import { jsx } from "react/jsx-runtime";
import { useCallback } from "react";
function BaseButton(props) {
  const {
    as,
    onClick,
    defaultOnClick,
    children,
    buttonRef,
    ...passthroughProps
  } = props;
  const handleOnClick = useCallback(
    (event) => {
      if (onClick) {
        const clickShouldContinue = onClick(event);
        if (typeof clickShouldContinue === "boolean" && clickShouldContinue === false || (event == null ? void 0 : event.defaultPrevented))
          return;
      }
      defaultOnClick == null ? void 0 : defaultOnClick(event);
    },
    [defaultOnClick, onClick]
  );
  const Component = as || "button";
  return /* @__PURE__ */ jsx(Component, { ref: buttonRef, onClick: handleOnClick, ...passthroughProps, children });
}
export {
  BaseButton
};
//# sourceMappingURL=BaseButton.mjs.map
