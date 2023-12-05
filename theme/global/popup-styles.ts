import { POPUP_HEIGHT, POPUP_WIDTH } from '@shared/constants';

// FIXME 4370 task #5 - test all popout headers + scroll behaviour (virtuoso included)
// Try get rid of these custom styles if we can
export const popupStyles = {
  '.mode__popup': {
    'html,body, #app, .radix-themes': {
      height: `${POPUP_HEIGHT}px`,
      // setting maxHeight / minHeight stops weird scroll on Session is locked in extension view
      // if set minHeight to 100vh then extension barely opens!
      maxHeight: '100vh',
      // the extension doesn't actually open to POPUP_HEIGHT and if minHeight higher than 600px we can scroll on unlock screen
      minHeight: `600px`,
      width: `${POPUP_WIDTH}px`,
      scrollbarWidth: 'none',

      // Only add overflow scroll on non-firefox browsers
      '@supports not (-moz-appearance: none)': {
        overflowY: 'scroll', // TODO 4370 look into disabling this and having it only on page container
      },

      '::-webkit-scrollbar': {
        display: 'none',
        width: 0,
      },
    },
  },
};
