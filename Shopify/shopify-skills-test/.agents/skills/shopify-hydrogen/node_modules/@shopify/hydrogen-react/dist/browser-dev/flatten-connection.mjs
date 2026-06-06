function flattenConnection(connection) {
  if (!connection) {
    const noConnectionErr = `flattenConnection(): needs a 'connection' to flatten, but received '${connection ?? ""}' instead.`;
    {
      throw new Error(noConnectionErr);
    }
  }
  if ("nodes" in connection) {
    return connection.nodes;
  }
  if ("edges" in connection && Array.isArray(connection.edges)) {
    return connection.edges.map((edge) => {
      if (!(edge == null ? void 0 : edge.node)) {
        throw new Error(
          "flattenConnection(): Connection edges must contain nodes"
        );
      }
      return edge.node;
    });
  }
  {
    console.warn(
      `flattenConnection(): The connection did not contain either "nodes" or "edges.node". Returning an empty array.`
    );
  }
  return [];
}
export {
  flattenConnection
};
//# sourceMappingURL=flatten-connection.mjs.map
