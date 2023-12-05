import { breakpoints } from '@leather-wallet/tokens';

import { POPUP_HEIGHT, POPUP_WIDTH } from '../src/shared/constants';

export const customViewports = {
  extension: {
    name: 'Extension Popout',
    styles: {
      width: `${POPUP_WIDTH}px`,
      height: `${POPUP_HEIGHT}px`,
    },
  },
  sm: {
    name: 'sm',
    styles: {
      width: breakpoints.sm,
      height: '100%',
    },
  },
  md: {
    name: 'md',
    styles: {
      width: breakpoints.md,
      height: '100%',
    },
  },
  lg: {
    name: 'lg',
    styles: {
      width: breakpoints.lg,
      height: '100%',
    },
  },
  xl: {
    name: 'xl',
    styles: {
      width: breakpoints.xl,
      height: '100%',
    },
  },
  '2xl': {
    name: '2xl',
    styles: {
      width: breakpoints['2xl'],
      height: '100%',
    },
  },
};
