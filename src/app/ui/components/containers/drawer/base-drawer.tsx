import { ReactNode, Suspense, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { Box, Flex, FlexProps } from 'leather-styles/jsx';

import { noop } from '@shared/utils';

import { useEventListener } from '@app/common/hooks/use-event-listener';
import { useOnClickOutside } from '@app/common/hooks/use-onclickoutside';

import { DrawerHeader } from '../headers/drawer-header';
import { ModalWrapper } from './modal-wrapper';

function useDrawer(isShowing: boolean, onClose: () => void, pause?: boolean) {
  const ref = useRef(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isShowing && e.key === 'Escape') {
        onClose();
      }
    },
    [onClose, isShowing]
  );

  useOnClickOutside(ref, !pause && isShowing ? onClose : null);
  useEventListener('keydown', handleKeyDown);

  return ref;
}

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
export function BaseDrawer({
  children,
  enableGoBack,
  isShowing,
  isWaitingOnPerformedAction,
  onClose,
  pauseOnClickOutside,
  title,
  waitingOnPerformedActionMessage,
}: BaseDrawerProps) {
  const ref = useDrawer(isShowing, onClose ? onClose : noop, pauseOnClickOutside);
  const navigate = useNavigate();

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
    <ModalWrapper isShowing={isShowing}>
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
        borderTopLeftRadius="lg"
        borderTopRightRadius="lg"
        borderBottomLeftRadius={[0, 0, 'lg']}
        borderBottomRightRadius={[0, 0, 'lg']}
        // position="relative"
        mt={['auto', 'auto', 'unset']}
        // maxHeight={['calc(100vh - 24px)', 'calc(100vh - 96px)']}
        // height is 100vh + height of page header it obscures
        // should remove these max heights but they help with create-account it seems
        maxHeight={['calc(100vh + 80px)', 'calc(100vh - 96px)']}
        zIndex={1}
      >
        <Box
          css={{
            overflowY: 'scroll',
            '&::-webkit-scrollbar': {
              display: 'none',
            },
          }}
        >
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
        </Box>
      </Flex>
    </ModalWrapper>
  );
}
