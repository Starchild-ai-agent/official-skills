import { jsx } from "react/jsx-runtime";
import { Image } from "./Image.mjs";
import { Video } from "./Video.mjs";
import { ExternalVideo } from "./ExternalVideo.mjs";
import { ModelViewer } from "./ModelViewer.mjs";
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
          throw new Error(noDataImage);
        }
      }
      return /* @__PURE__ */ jsx(
        Image,
        {
          ...passthroughProps,
          ...mediaOptions == null ? void 0 : mediaOptions.image,
          data: data.image
        }
      );
    }
    case "Video": {
      return /* @__PURE__ */ jsx(Video, { ...passthroughProps, ...mediaOptions == null ? void 0 : mediaOptions.video, data });
    }
    case "ExternalVideo": {
      return /* @__PURE__ */ jsx(
        ExternalVideo,
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
        /* @__PURE__ */ jsx(
          ModelViewer,
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
        throw new Error(typenameMissingMessage);
      }
    }
  }
}
export {
  MediaFile
};
//# sourceMappingURL=MediaFile.mjs.map
