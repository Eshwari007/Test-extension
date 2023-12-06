import { ReactNode } from 'react';

import { Box, Flex } from 'leather-styles/jsx';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';

interface ModalWrapperProps {
  children: ReactNode;
  isShowing: boolean; // TODO try refactor away this isShowing
}

export function ModalWrapper({ children, isShowing }: ModalWrapperProps) {
  // show as modal on larger sizes
  const isAtleastBreakpointMd = useViewportMinWidth('md');

  if (isAtleastBreakpointMd) {
    return (
      <Flex
        id="modal-flex"
        display={isShowing ? 'flex' : 'none'}
        bg="overlay"
        transition="transition"
        position="fixed"
        top={0}
        left={0}
        height="100%"
        // pt="space.05"
        width="100%"
        alignItems="center"
        justifyContent="center"
        flexDirection="column"
        // zIndex={1000}
        style={{
          pointerEvents: !isShowing ? 'none' : 'unset',
          userSelect: !isShowing ? 'none' : 'unset',
          willChange: 'background',
        }}
      >
        {children}
      </Flex>
    );
  } else {
    return (
      <Box position="absolute" top="-80px" width="100%" zIndex={1}>
        {children}
      </Box>
    );
  }
}
