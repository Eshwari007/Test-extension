import { css } from 'leather-styles/css';

export const virtuosoContainerStyle = css.raw({
  '&::-webkit-scrollbar': {
    display: 'none',
  },
  maxHeight: { base: '75vh', md: '100%' },
});

export const virtuosoStyle = css.raw({
  paddingTop: '24px',
  minHeight: { base: '85vh', md: '70vh' },
});
