import { ReactNode, memo } from 'react';

import { Flex } from 'leather-styles/jsx';

// FIXME - !important - test POPUP view ! need to figure that out

interface ModalWrapperProps {
  children: ReactNode; // use HasChildren ?
  isShowing: boolean; // TODO try refactor away this isShowing
  isAtleastBreakpointMd: boolean;
  title?: ReactNode; // hacky but get it working for now
}

export const ModalWrapper = memo(
  ({ children, isShowing, isAtleastBreakpointMd, title }: ModalWrapperProps) => {
    console.log('isAtleastBreakpointMd isShowing', isAtleastBreakpointMd, isShowing, title);
    return (
      <Flex
        id="modal-flex"
        display={isShowing ? 'flex' : 'none'}
        bg="overlay"
        transition="transition"
        // position={isAtleastBreakpointMd ? 'fixed' : 'absolute'}
        position="fixed"
        // TODO fix headers properly
        // FIXME - make this better this works for 'receive' as it has a taller header but obscures Select account
        // need to set as 0 on wide and account for headers on small
        top={isAtleastBreakpointMd ? 0 : typeof title !== 'string' ? 0 : '-80px'} // need to set this -80 to cover tyhe header for not select account in small view - do it better
        left={0}
        // PETE this is what breaks the bg colour - if not height
        height={isAtleastBreakpointMd ? '100%' : undefined}
        // height="100vh"
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
  }
);
