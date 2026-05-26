const React = require("react");
const { View } = require("react-native");

const Svg = ({ children }) => React.createElement(View, { testID: "svg" }, children);
const Circle = (props) => React.createElement(View, { testID: "circle", ...props });
const Path = (props) => React.createElement(View, { testID: "path", ...props });
const G = ({ children }) => React.createElement(View, null, children);

module.exports = Svg;
module.exports.default = Svg;
module.exports.Svg = Svg;
module.exports.Circle = Circle;
module.exports.Path = Path;
module.exports.G = G;
