import { ReactNode } from 'react';

import * as Dialog from '@radix-ui/react-dialog';
import { css } from 'leather-styles/css';

interface ModalLayoutProps {
  children: ReactNode;
  title: ReactNode;
  footer?: ReactNode;
  onClose?(): void; // check as this always needs to be provided
}
export function Modal({ children, onClose, title, footer }: ModalLayoutProps) {
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
            onPointerDownOutside={onClose}
            className={css({
              backgroundColor: 'accent.background-primary',
              borderRadius: '6px',
              boxShadow:
                'hsl(206 22% 7% / 35%) 0px 10px 38px -10px, hsl(206 22% 7% / 20%) 0px 10px 20px -15px',
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: { base: '100vw', md: '90vw' },
              height: { base: '100vh', md: 'unset' },
              maxWidth: { base: '100vw', md: '450px' },
              maxHeight: { base: '100vh', md: '85vh' },
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
