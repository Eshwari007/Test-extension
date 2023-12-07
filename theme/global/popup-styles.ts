// #4250 TODO seems to be a discrepancy between this and
// POPUP_CENTER_WIDTH / POPUP_CENTER_HEIGHT
import { POPUP_CENTER_HEIGHT, POPUP_CENTER_WIDTH } from '@shared/constants';

const maxWidth = `${POPUP_CENTER_WIDTH}px`;
const maxHeight = `${POPUP_CENTER_HEIGHT}px`;

export const popupStyles = {
  '.mode__popup': {
    'html,body': {
      minWidth: maxWidth,
      maxWidth: maxWidth,
      minHeight: maxHeight,
      maxHeight: maxHeight,
      scrollbarWidth: 'none',

      // Only add overflow scroll on non-firefox browsers
      '@supports not (-moz-appearance: none)': {
        overflowY: 'scroll',
      },

      '::-webkit-scrollbar': {
        display: 'none',
        width: 0,
      },
    },
  },
  // '.mode__popup-center': {
  //   '&, body': {
  //     height: '100%',
  //     width: '100%',
  //   },
  // },
};
