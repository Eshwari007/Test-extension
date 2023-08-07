import { mapObject } from '../helpers.ts';
import { css } from '../css/index.ts';

const spacerConfig = {
transform(props, { map }) {
  const { size, ...rest } = props;
  return {
    alignSelf: "stretch",
    justifySelf: "stretch",
    flex: map(size, (v) => v == null ? "1" : `0 0 ${v}`),
    ...rest
  };
}}

export const getSpacerStyle = (styles = {}) => spacerConfig.transform(styles, { map: mapObject })

export const spacer = (styles) => css(getSpacerStyle(styles))
spacer.raw = (styles) => styles