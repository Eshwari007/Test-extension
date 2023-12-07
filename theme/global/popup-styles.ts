// #4250 TODO seems to be a discrepancy between this and
// POPUP_CENTER_WIDTH / POPUP_CENTER_HEIGHT
const maxWidth = '392px';
const maxHeight = '600px';

export const popupStyles = {
  // #4250 I don't think this is ever used anywhere
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
  '.mode__popup-center': {
    '&, body': {
      height: '100%',
      width: '100%',
    },
  },
};
