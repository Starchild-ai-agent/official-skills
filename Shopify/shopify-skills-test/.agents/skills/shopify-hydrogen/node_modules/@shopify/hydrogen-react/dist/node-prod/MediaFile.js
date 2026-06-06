"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const Image = require("./Image.js");
const Video = require("./Video.js");
const ExternalVideo = require("./ExternalVideo.js");
const ModelViewer = require("./ModelViewer.js");
function MediaFile({
  data,
  mediaOptions,
  ...passthroughProps
}) {
  switch (data.__typename) {
    case "MediaImage": {
      if (!data.image) {
        const noDataImage = `<MediaFile/>: 'data.image' does not exist for __typename of 'MediaImage'; rendering 'null' by default.`;
        {
          console.warn(noDataImage);
          return null;
        }
      }
      return /* @__PURE__ */ jsxRuntime.jsx(
        Image.Image,
        {
          ...passthroughProps,
          ...mediaOptions == null ? void 0 : mediaOptions.image,
          data: data.image
        }
      );
    }
    case "Video": {
      return /* @__PURE__ */ jsxRuntime.jsx(Video.Video, { ...passthroughProps, ...mediaOptions == null ? void 0 : mediaOptions.video, data });
    }
    case "ExternalVideo": {
      return /* @__PURE__ */ jsxRuntime.jsx(
        ExternalVideo.ExternalVideo,
        {
          ...passthroughProps,
          ...mediaOptions == null ? void 0 : mediaOptions.externalVideo,
          data
        }
      );
    }
    case "Model3d": {
      return (
        // @ts-expect-error There are issues with the inferred HTML attribute types here for ModelViewer (and contentEditable), but I think that's a little bit beyond me at the moment
        /* @__PURE__ */ jsxRuntime.jsx(
          ModelViewer.ModelViewer,
          {
            ...passthroughProps,
            ...mediaOptions == null ? void 0 : mediaOptions.modelViewer,
            data
          }
        )
      );
    }
    default: {
      const typenameMissingMessage = `<MediaFile /> requires the '__typename' property to exist on the 'data' prop in order to render the matching sub-component for this type of media.`;
      {
        console.error(`${typenameMissingMessage}  Rendering 'null' by default`);
        return null;
      }
    }
  }
}
exports.MediaFile = MediaFile;
//# sourceMappingURL=MediaFile.js.map
