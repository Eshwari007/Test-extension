import { defineGlobalStyles } from '@pandacss/dev';

import { fullPageStyles } from './full-page-styles';
import { popupStyles } from './popup-styles';

// 4370 TODO audit the use of this file as we are pretty close to not needing it
// - could set some styles in the <Container where radix.css also loaded
// - try make UI things more modular, self contained and independant

// ts-unused-exports:disable-next-line
export const globalCss = defineGlobalStyles({
  'html, body': {
    backgroundColor: 'accent.background-primary',
  },
  button: {
    cursor: 'pointer',
  },
  // 4370 TODO check this - it was inconsistent with our md breakpoint so we see a weird state between 600 - 768px
  '@media (min-width: 768px)': {
    'html, body': {
      backgroundColor: 'accent.background-secondary',
    },
  },
  body: {
    '&.no-scroll, &.no-scroll .main-content': {
      overflow: 'hidden',
    },
  },
  ...fullPageStyles,
  ...popupStyles,
});
