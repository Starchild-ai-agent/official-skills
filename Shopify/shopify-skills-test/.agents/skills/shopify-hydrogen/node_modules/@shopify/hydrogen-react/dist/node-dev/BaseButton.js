"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const React = require("react");
function BaseButton(props) {
  const {
    as,
    onClick,
    defaultOnClick,
    children,
    buttonRef,
    ...passthroughProps
  } = props;
  const handleOnClick = React.useCallback(
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
  return /* @__PURE__ */ jsxRuntime.jsx(Component, { ref: buttonRef, onClick: handleOnClick, ...passthroughProps, children });
}
exports.BaseButton = BaseButton;
//# sourceMappingURL=BaseButton.js.map
