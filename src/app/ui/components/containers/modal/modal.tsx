import { ReactNode, useState } from 'react';

import * as Dialog from '@radix-ui/react-dialog';
import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { css } from 'leather-styles/css';
import { Box, Flex, HStack, Stack, styled } from 'leather-styles/jsx';
import { title } from 'process';

import { HasChildren } from '@app/common/has-children';
import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
// import { isPopupMode } from '@app/common/utils';
import { LeatherButton } from '@app/ui/components/button';
import { CheckmarkIcon } from '@app/ui/components/icons/checkmark-icon';
import { LeatherIcon } from '@app/ui/components/icons/leather-icon';

interface ModalLayoutProps {
  children: ReactNode;
  title: ReactNode;
  footer?: ReactNode;
}

export function Modal({ children, title, footer }: ModalLayoutProps) {
  const [open, setOpen] = useState(false);
  const isAtleastBreakpointMd = useViewportMinWidth('md');
  return (
    <Dialog.Root open>
      <Dialog.Portal>
        <Dialog.Overlay
          className={css({
            backgroundColor: 'overlay',
            position: 'fixed',
            inset: 0,
            animation: 'overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
          })}
        >
          <Dialog.Content
            // onPointerDownOutside={() => setOpen(!open)}
            className={css({
              backgroundColor: 'accent.background-primary',
              borderRadius: '6px',
              boxShadow:
                'hsl(206 22% 7% / 35%) 0px 10px 38px -10px, hsl(206 22% 7% / 20%) 0px 10px 20px -15px',
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: isAtleastBreakpointMd ? '90vw' : '100vw',
              height: isAtleastBreakpointMd ? undefined : '100vh',
              maxWidth: '450px',
              maxHeight: isAtleastBreakpointMd ? '85vh' : '100vh',
              // padding: '25px',
              animation: 'contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
            })}
          >
            {/*  Dialog.Title + Dialog.Close are for screen readers */}
            <Dialog.Title />
            {title}
            {children}

            {footer}
            <Dialog.Close />
          </Dialog.Content>
        </Dialog.Overlay>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
