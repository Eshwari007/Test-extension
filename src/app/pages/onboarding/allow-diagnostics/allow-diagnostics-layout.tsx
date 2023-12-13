import { useState } from 'react';

import * as Dialog from '@radix-ui/react-dialog';
import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { css } from 'leather-styles/css';
import { Box, Flex, HStack, Stack, styled } from 'leather-styles/jsx';

// import { isPopupMode } from '@app/common/utils';
import { LeatherButton } from '@app/ui/components/button';
import { CheckmarkIcon } from '@app/ui/components/icons/checkmark-icon';
import { LeatherIcon } from '@app/ui/components/icons/leather-icon';

interface ReasonToAllowDiagnosticsProps {
  text: string;
}
function ReasonToAllowDiagnostics({ text }: ReasonToAllowDiagnosticsProps) {
  return (
    <Flex textStyle="body.02">
      <Box mr="space.02" mt="3px">
        <CheckmarkIcon />
      </Box>
      <Box>{text}</Box>
    </Flex>
  );
}

interface AllowDiagnosticsLayoutProps {
  onUserAllowDiagnostics(): void;
  onUserDenyDiagnostics(): void;
}

// // #4250 TODO
// Popup mode is just slightly wider than extension view
// isPopupMode() returns true for extension / popup
// could also change sm breakpoint
// sm: '398px', -> sm: '442px',

export function AllowDiagnosticsLayout(props: AllowDiagnosticsLayoutProps) {
  const { onUserAllowDiagnostics, onUserDenyDiagnostics } = props;
  const [open, setOpen] = useState(true);
  return (
    <Dialog.Root open={open}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={css({
            backgroundColor: 'transparent',
            position: 'fixed',
            inset: 0,
            animation: 'overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
          })}
        >
          <Dialog.Content
            onPointerDownOutside={() => setOpen(!open)}
            className={css({
              backgroundColor: 'accent.background-primary',
              borderRadius: '6px',
              boxShadow:
                'hsl(206 22% 7% / 35%) 0px 10px 38px -10px, hsl(206 22% 7% / 20%) 0px 10px 20px -15px',
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '90vw',
              maxWidth: '450px',
              maxHeight: '85vh',
              padding: '25px',
              animation: 'contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',

              // OLD
              // width: '500px',
              // marginY: 'space.03',
              // backgroundColor: 'accent.background-primary',
              // adding a minHeight here works for extension/popup but we lose margins
              // minHeight: isPopupMode() ? '600px' : undefined,
            })}
          >
            <LeatherIcon width="72px" />
            <styled.h1 textStyle="heading.03" mt={['space.05', 'space.08']}>
              Help us improve
            </styled.h1>
            <styled.p mt={['space.03', 'space.05']} textStyle="heading.05">
              Leather would like to gather deidentified service usage data to help improve the
              experience of the wallet.
            </styled.p>

            <Stack mt={['space.04', 'space.05']} textStyle="body.01">
              <ReasonToAllowDiagnostics text="Send data about page views, clicks, and errors" />
              <ReasonToAllowDiagnostics text="This data is tied to randomly-generated IDs, and not personal data such as your Stacks address, keys, balances or IP address" />
              <ReasonToAllowDiagnostics text="This data is used to generate and send crash reports, help fix errors, and analyze statistics" />
            </Stack>

            <HStack mt={['space.07', 'space.11']} gap="space.04">
              <LeatherButton
                fullWidth
                variant="outline"
                onClick={() => onUserDenyDiagnostics()}
                data-testid={OnboardingSelectors.DenyAnalyticsBtn}
              >
                Deny
              </LeatherButton>
              <LeatherButton
                autoFocus
                fullWidth
                data-testid={OnboardingSelectors.AllowAnalyticsBtn}
                onClick={onUserAllowDiagnostics}
              >
                Allow
              </LeatherButton>
            </HStack>

            <Dialog.Title />
            <Dialog.Close />
          </Dialog.Content>
        </Dialog.Overlay>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
