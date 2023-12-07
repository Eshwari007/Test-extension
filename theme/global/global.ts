import { defineGlobalStyles } from '@pandacss/dev';

import { fullPageStyles } from './full-page-styles';
// import { popupCenterStyles } from './popup-center-styles';
import { popupStyles } from './popup-styles';
import { radixStyles, radixTabStyles } from './radix-styles';
import { tippyStyles } from './tippy-styles';

// ts-unused-exports:disable-next-line
export const globalCss = defineGlobalStyles({
  // TODO: investigate cleaner solution
  // this is needed to prevent BG scroll in extension view
  // FIXME PETE - need to make sure scroll works in popout mode
  html: {
    overflow: 'hidden',
  },
  'html, body': {
    backgroundColor: 'accent.background-primary',
  },
  button: {
    cursor: 'pointer',
  },
  '@media (min-width: 600px)': {
    'html, body': {
      backgroundColor: 'accent.background-secondary',
    },
  },
  body: {
    overflowY: 'scroll', //  TODO: investigate this adds an un-necessary scroll bar to popout mode
    '&.no-scroll, &.no-scroll .main-content': {
      overflow: 'hidden',
    },
  },
  ...fullPageStyles,
  ...popupStyles,
  // ...popupCenterStyles,
  ...tippyStyles,
  ...radixStyles,
  ...radixTabStyles,
});
