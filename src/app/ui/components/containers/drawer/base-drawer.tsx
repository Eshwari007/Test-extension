// TODO - not sure why we call this a drawer when it's a modal
// 4370 TODO - can investigate swapping this for radix dialog and using modal true / false
import { ReactNode, Suspense, memo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Box, Flex, FlexProps } from 'leather-styles/jsx';

import { noop } from '@shared/utils';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';

import { Footer } from '../footers/footer';
import { DrawerHeader } from '../headers/drawer-header';
import { Modal } from '../modal/modal';
import { useDrawer } from './hooks/use-drawer';
import { ModalWrapper } from './modal-wrapper';

interface BaseDrawerProps extends Omit<FlexProps, 'title'> {
  children?: ReactNode;
  enableGoBack?: boolean;
  footer?: ReactNode;
  isShowing: boolean;
  isWaitingOnPerformedAction?: boolean;
  onClose?(): void;
  pauseOnClickOutside?: boolean;
  title?: ReactNode;
  waitingOnPerformedActionMessage?: string;
}
export const BaseDrawer = memo(
  ({
    children,
    enableGoBack,
    footer,
    isShowing,
    isWaitingOnPerformedAction,
    onClose,
    pauseOnClickOutside,
    title,
    waitingOnPerformedActionMessage,
  }: BaseDrawerProps) => {
    const ref = useDrawer(isShowing, onClose ? onClose : noop, pauseOnClickOutside);
    const navigate = useNavigate();

    const isAtleastBreakpointMd = useViewportMinWidth('md');
    const onGoBack = () => navigate(-1);

    // debugger;
    // flashing has to be something to do with height, maybe the one I set undefined?
    // - see in this debugger it renders a larger drawer then reduces the size

    // TODO investigate useScrollLock
    // useScrollLock works but somehow messes up display of modal?
    // useScrollLock(true);

    // PETE - stop now and return to fix this
    // - need overlay to be full height in modal
    // - need to block BG scroll

    // sometimes this adds an un-necessary scrollbar
    useEffect(() => {
      document.body.style.overflowY = 'hidden';
      return () => {
        document.body.style.overflowY = 'auto';
      };
    }, []);

    console.log('typeof title', title, typeof title);
    // if (!isShowing) return null;

    return (
      <Modal
        title={
          <DrawerHeader
            enableGoBack={enableGoBack}
            isWaitingOnPerformedAction={isWaitingOnPerformedAction}
            onClose={onClose}
            onGoBack={onGoBack}
            title={title}
            waitingOnPerformedActionMessage={waitingOnPerformedActionMessage}
            data-testId="drawer-header"
          />
        }
        footer={footer ? <Footer>{footer}</Footer> : undefined}
      >
        {children}
      </Modal>
    );

    // TODO - clean up this isAtleastBreakpointMd logic
    return (
      <ModalWrapper
        data-testid="modal-wrapper"
        isShowing={isShowing}
        isAtleastBreakpointMd={isAtleastBreakpointMd}
        title={title}
      >
        <Flex
          id="drawer-flex"
          flexDirection="column"
          // flexGrow={0}
          ref={ref}
          opacity={isShowing ? 1 : 0}
          transform={isShowing ? 'none' : 'translateY(35px)'}
          transition={isShowing ? 'transition' + ' 0.1s' : 'transition'}
          transitionDuration="0.4s"
          // willChange="transform, opacity"
          // FIXME - make this better this works for 'receive' as it has a taller header but obscures Select account
          // need to get this working properly in popup mode - for change theme it makes it too high
          top={0}
          // position={isAtleastBreakpointMd ? 'fixed' : 'absolute'}
          position="fixed" // fixed to stop BG scroll?
          width="100%"
          // ??? without setting max-width here this messes up everything and create account button breaks
          // should be the same max width on all sizes now
          maxWidth={['768px', '768px', '472px']}
          minHeight={isAtleastBreakpointMd ? undefined : '100vh'}
          bg="accent.background-primary"
          // removing this border on small gives the impression of it being a full page
          borderRadius={[0, 0, 'lg']}
          mt={isAtleastBreakpointMd ? '20vh' : 'unset'}
          zIndex={1}
        >
          {/* TODO check what this Box did / does - nothing I think as receive + select account OK */}
          <Box
            css={{
              overflowY: 'scroll',
              '&::-webkit-scrollbar': {
                display: 'none',
              },
            }}
          >
            {/* // FIXME this should be passed in as a slot like Footer */}
            <DrawerHeader
              enableGoBack={enableGoBack}
              isWaitingOnPerformedAction={isWaitingOnPerformedAction}
              onClose={onClose}
              onGoBack={onGoBack}
              title={title}
              waitingOnPerformedActionMessage={waitingOnPerformedActionMessage}
              data-testId="drawer-header"
            />
            {/* TODO check if this flex is even needed
            try add padding from sign-out-confirm here to make it consistent
          */}
            <Flex maxHeight="100%" flexGrow={1} flexDirection="column">
              <Suspense fallback={<></>}>{children}</Suspense>
            </Flex>
            {/* {children} */}
            {footer && <Footer>{footer}</Footer>}
          </Box>
        </Flex>
      </ModalWrapper>
    );
  }
);
