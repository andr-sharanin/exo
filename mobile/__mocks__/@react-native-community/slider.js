const React = require("react");
const { View } = require("react-native");

const Slider = ({ testID, value, minimumValue, maximumValue, onValueChange, ...rest }) =>
  React.createElement(View, { testID: testID || "slider", ...rest });

module.exports = Slider;
module.exports.default = Slider;
