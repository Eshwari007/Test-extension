import { ReactNode, memo } from 'react';

import * as RadixDialog from '@radix-ui/react-dialog';
import { css } from 'leather-styles/css';
import { Box } from 'leather-styles/jsx';

import { Header } from '@app/ui/components/containers/headers/header';

export interface DialogProps {
  children?: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  isShowing: boolean;
  isWaitingOnPerformedAction?: boolean;
  onGoBack?(): void;
  onClose?(): void;
  pauseOnClickOutside?: boolean; // FIXME - seem to have lost what this does in useDrawer() I think it blocked close on click outside?
  title?: string;
  // waitingOnPerformedActionMessage?: string;
}

//  TODO 4370 task #1  - manual task to sift through all Dialogs and read the props
export const Dialog = memo(
  ({
    children,
    header, //so far only passed in my receive-modal + swap-choose
    footer,
    isWaitingOnPerformedAction,
    onGoBack,
    onClose,
    title,
    isShowing,
  } // waitingOnPerformedActionMessage,
  : DialogProps) => {
    if (!isShowing) return null;

    return (
      <RadixDialog.Root open>
        <RadixDialog.Portal>
          <RadixDialog.Overlay
            className={css({
              backgroundColor: 'overlay',
              position: 'fixed',
              inset: 0,
              animation: 'overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
            })}
          >
            <RadixDialog.Content
              onPointerDownOutside={onClose}
              className={css({
                backgroundColor: 'accent.background-primary',
                // remove borderRadius on small to give impression of full page
                borderRadius: { base: '0', md: 'lg' },
                boxShadow:
                  'hsl(206 22% 7% / 35%) 0 10px 38px -10px, hsl(206 22% 7% / 20%) 0 10px 20px -15px',
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
              <Box maxHeight="100vh" overflowY="hidden">
                {/*  PETE - now dialogs are always showing a header! - not required 
                
                maybe I need to pass in header instead of title for those? 
                and be able to pass in big/ small text? 
                make them like the receive modal is now
                maybe simpler answer here is to have a dialog variant?

                could need to split between full page and extension headers also 
                */}
                {/* TODO check if this box is even needed now */}
                {/* <Box
        className={css({
          position: 'fixed',
          width: '100%',
          height: '68px',
          padding: '16px',
        })}
      > */}
                {header ? (
                  header
                ) : (
                  <Header
                    variant="page"
                    isWaitingOnPerformedAction={isWaitingOnPerformedAction}
                    onClose={onClose}
                    onGoBack={onGoBack}
                    title={title} // title only used here and passed in by 15 of dialogs
                    // waitingOnPerformedActionMessage={waitingOnPerformedActionMessage}
                  />
                )}

                {/* </Box> */}
                <Box
                  className={css({
                    overflowY: 'scroll',
                    '&::-webkit-scrollbar': {
                      display: 'none',
                    },
                  })}
                >
                  {children}
                </Box>
                {footer}
              </Box>
            </RadixDialog.Content>
          </RadixDialog.Overlay>
        </RadixDialog.Portal>
      </RadixDialog.Root>
    );
  }
);
