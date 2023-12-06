import { ReactNode, memo } from 'react';

import { Box, Flex } from 'leather-styles/jsx';
import { title } from 'process';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';

interface ModalWrapperProps {
  children: ReactNode;
  isShowing: boolean; // TODO try refactor away this isShowing
  // isAtleastBreakpointMd: boolean;
}

// PETe need to fix this - get it to move smoothly between views without flashing the ?UI

// NEXT;

export const ModalWrapper = memo(({ children, isShowing }: ModalWrapperProps) => {
  // console.log('isAtleastBreakpointMd', isAtleastBreakpointMd);
  // show as modal on larger sizes

  const isAtleastBreakpointMd = useViewportMinWidth('md');
  // PETE - doing this switch causes an un-necessary re-render when moving between modals
  // that causes the UI to flash
  // not really noticable for extension view but looks bad in desktop
  if (isAtleastBreakpointMd) {
    return (
      <Flex
        id="modal-flex"
        display={isShowing ? 'flex' : 'none'}
        bg="overlay"
        transition="transition"
        position={isAtleastBreakpointMd ? 'fixed' : 'absolute'}
        top={isAtleastBreakpointMd ? 0 : typeof title === 'string' ? 0 : '-80px'} // FIXME - make this better this works for 'receive' as it has a taller header but obscures Select account
        left={0}
        height="100%"
        // pt="space.05"
        width="100%"
        alignItems="center"
        justifyContent="center"
        flexDirection="column"
        zIndex={1} // Bizarrely, without this the Select Account view doesn't show on wide view
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
      <Box
        position="absolute"
        // FIXME - make this better this works for 'receive' as it has a taller header but obscures Select account
        top={typeof title === 'string' ? 0 : '-80px'}
        width="100%"
        zIndex={1}
      >
        {children}
      </Box>
    );
  }
});
