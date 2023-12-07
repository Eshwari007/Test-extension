// TODO - not sure why we call this a drawer when it's a modal
// 4370 TODO - can investigate swapping this for radix dialog and using modal true / false
import { ReactNode, Suspense, memo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Flex, FlexProps } from 'leather-styles/jsx';

import { noop } from '@shared/utils';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';

import { DrawerHeader } from '../headers/drawer-header';
import { useDrawer } from './hooks/use-drawer';
import { ModalWrapper } from './modal-wrapper';

interface BaseDrawerProps extends Omit<FlexProps, 'title'> {
  children?: ReactNode;
  enableGoBack?: boolean;
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
    // TODO investigate useScrollLock
    // useScrollLock works but somehow messes up display of modal?
    // useScrollLock(true);

    useEffect(() => {
      document.body.style.overflowY = 'hidden';
      return () => {
        document.body.style.overflowY = 'scroll';
      };
    }, []);

    return (
      <ModalWrapper isShowing={isShowing} isAtleastBreakpointMd={isAtleastBreakpointMd}>
        <Flex
          id="drawer-flex"
          flexDirection="column"
          flexGrow={0}
          ref={ref}
          opacity={isShowing ? 1 : 0}
          transform={isShowing ? 'none' : 'translateY(35px)'}
          transition={isShowing ? 'transition' + ' 0.1s' : 'transition'}
          transitionDuration="0.4s"
          willChange="transform, opacity"
          width="100%"
          maxWidth={['768px', '768px', '472px']} // ???
          bg="accent.background-primary"
          // removing this border on small gives the impression of it being a full page
          borderRadius={[0, 0, 'lg']}
          mt={['auto', 'auto', 'unset']}
          // maxHeight={['calc(100vh - 24px)', 'calc(100vh - 96px)']}
          // height is 100vh + height of page header it obscures
          // should remove these max heights but they help with create-account it seems
          maxHeight={['calc(100vh + 80px)', 'calc(100vh - 96px)']}
          zIndex={1}
        >
          {/* TODO check what this Box did / does - nothing I think as receive + select account OK */}
          {/* <Box
            css={{
              overflowY: 'scroll',
              '&::-webkit-scrollbar': {
                display: 'none',
              },
            }}
          > */}
          <DrawerHeader
            enableGoBack={enableGoBack}
            isWaitingOnPerformedAction={isWaitingOnPerformedAction}
            onClose={onClose}
            onGoBack={onGoBack}
            title={title}
            waitingOnPerformedActionMessage={waitingOnPerformedActionMessage}
          />
          <Flex maxHeight="100%" flexGrow={1} flexDirection="column">
            <Suspense fallback={<></>}>{children}</Suspense>
          </Flex>
          {/* </Box> */}
        </Flex>
      </ModalWrapper>
    );
  }
);
