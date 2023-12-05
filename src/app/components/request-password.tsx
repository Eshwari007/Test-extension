import { FormEvent, ReactNode, useCallback, useState } from 'react';

import { SettingsSelectors } from '@tests/selectors/settings.selectors';
import { Stack, styled } from 'leather-styles/jsx';

import { useAnalytics } from '@app/common/hooks/analytics/use-analytics';
import { useKeyActions } from '@app/common/hooks/use-key-actions';
import { buildEnterKeyEvent } from '@app/common/hooks/use-modifier-key';
import { WaitingMessages, useWaitingMessage } from '@app/common/utils/use-waiting-message';
import { Button } from '@app/ui/components/button/button';
import { Footer } from '@app/ui/components/containers/footers/footer';
import { LeatherLogo } from '@app/ui/components/leather-logo';

// import { TwoColumnLayout } from '../ui/components/containers/two-column.layout';
import { ErrorLabel } from './error-label';

const waitingMessages: WaitingMessages = {
  '2': 'Verifying password…',
  '10': 'Still working…',
  '20': 'Almost there',
};

interface RequestPasswordProps {
  sessionLocked?: boolean;
  onSuccess(): void;
  title?: ReactNode;
  caption?: string;
}
export function RequestPassword({
  sessionLocked,
  title,
  caption,
  onSuccess,
}: RequestPasswordProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { unlockWallet } = useKeyActions();
  const analytics = useAnalytics();
  const [isRunning, waitingMessage, startWaitingMessage, stopWaitingMessage] =
    useWaitingMessage(waitingMessages);

  const submit = useCallback(async () => {
    const startUnlockTimeMs = performance.now();
    void analytics.track('start_unlock');
    startWaitingMessage();
    setError('');
    try {
      await unlockWallet(password);
      onSuccess?.();
    } catch (error) {
      setError('The password you entered is invalid');
    }
    stopWaitingMessage();
    const unlockSuccessTimeMs = performance.now();
    void analytics.track('complete_unlock', {
      durationMs: unlockSuccessTimeMs - startUnlockTimeMs,
    });
  }, [analytics, startWaitingMessage, stopWaitingMessage, unlockWallet, password, onSuccess]);

  if (sessionLocked) {
    // TODO #4370 revisit and test this screen with set-password

    return (
      <>
        <Stack
          backgroundColor="accent.background-primary"
          borderRadius="xs"
          width={{ base: '392px', md: '500px' }}
        >
          {/* // TODO #4370 add header */}
          <styled.header height="68px" p="space.04">
            <LeatherLogo
            // 4370 TODO - make logos the same
            // height="32px"
            // verticalAlign="middle"
            // px="space.02"
            />
          </styled.header>
          <Stack px="space.05" gap="space.05" minHeight={{ base: '100vh', md: '100px' }}>
            <styled.h2 textStyle="heading.03">{title}</styled.h2>
            <styled.input
              _focus={{ border: 'focus' }}
              autoCapitalize="off"
              autoComplete="off"
              autoFocus
              border="active"
              borderRadius="sm"
              data-testid={SettingsSelectors.EnterPasswordInput}
              disabled={isRunning}
              height="64px"
              onChange={(e: FormEvent<HTMLInputElement>) => {
                setError('');
                setPassword(e.currentTarget.value);
              }}
              onKeyUp={buildEnterKeyEvent(submit)}
              p="space.04"
              placeholder="Enter your password"
              ring="none"
              type="password"
              textStyle="body.02"
              value={password}
              width="100%"
            />
            {error && <ErrorLabel width="100%">{error}</ErrorLabel>}

            <styled.p
              textStyle={{ base: 'label.01', md: 'heading.05' }}
              mb="space.06"
              textAlign="left"
            >
              {(isRunning && waitingMessage) || caption}
            </styled.p>
          </Stack>

          <Footer>
            <Button
              fullWidth
              data-testid={SettingsSelectors.UnlockWalletBtn}
              disabled={isRunning || !!error}
              aria-busy={isRunning}
              onClick={submit}
            >
              Continue
            </Button>
          </Footer>
        </Stack>
      </>
    );
  }

  return null;
  // return (
  //   <>
  //     {/*
  //   new design was simplified so may not need much work here
  //   - TwoColumnLayout can go from here
  //   - this is the Locked session screen
  //   */}

  //     <TwoColumnLayout
  //       leftColumn={
  //         <>
  //           <styled.h1
  //             // textStyle={['heading.03', 'heading.03', 'heading.03', 'display.02']}
  //             textStyle={{ base: 'heading.03', lg: 'display.02' }}
  //             textAlign="left"
  //             mt="space.00"
  //             mb="space.06"
  //           >
  //             {title}
  //           </styled.h1>
  //           <styled.p
  //             textStyle={{ base: 'label.01', md: 'heading.05' }}
  //             mb="space.06"
  //             textAlign="left"
  //           >
  //             {(isRunning && waitingMessage) || caption}
  //           </styled.p>
  //         </>
  //       }
  //       rightColumn={
  //         <>
  //           <styled.h2
  //             textStyle="heading.03"
  //             mt="space.02"
  //             mb="space.04"
  //             hideBelow="sm"
  //             textAlign="center"
  //           >
  //             Your password
  //           </styled.h2>
  //           <Stack gap="space.04" alignItems="center" minHeight={{ base: '30vh', lg: '100px' }}>
  //             <styled.input
  //               _focus={{ border: 'focus' }}
  //               autoCapitalize="off"
  //               autoComplete="off"
  //               autoFocus
  //               border="active"
  //               borderRadius="sm"
  //               data-testid={SettingsSelectors.EnterPasswordInput}
  //               disabled={isRunning}
  //               height="64px"
  //               onChange={(e: FormEvent<HTMLInputElement>) => {
  //                 setError('');
  //                 setPassword(e.currentTarget.value);
  //               }}
  //               onKeyUp={buildEnterKeyEvent(submit)}
  //               p="space.04"
  //               placeholder="Enter your password"
  //               ring="none"
  //               type="password"
  //               textStyle="body.02"
  //               value={password}
  //               width="100%"
  //             />
  //             {error && <ErrorLabel width="100%">{error}</ErrorLabel>}
  //           </Stack>
  //           {/* <Box
  //             position="fixed"
  //             bottom="space.03"
  //             width="calc(100vw-32px)"
  //             //- works but feels wrong. should be out of this box in a footer
  //             // width="100vw"
  //             margin="auto"
  //             // padding="16px"
  //           > */}
  //           <Footer
  //           // px={{ base: 'space.00', lg: 'space.05' }}
  //           // px="space.00"
  //           // px={{ base: 'space.00', md: 'space.05' }}
  //           // position={{ base: 'fixed', md: 'sticky' }}
  //           >
  //             {/* // TODO fix this but better to pass padding with child?
  //       or pass in over-rides here - px'space.05', position 'fixed'

  //     // TODO fix this but better to pass padding with child
  //     px="space.05"
  //     */}
  //             {/*
  //     FIXME - more work needed here as this button looks bad in md view
  //     may need to start over with TwoColumnLayout

  //     OR swap in a different view for when in mobile - use page.layout in mobile instead of 2 column which is buggy
  //     */}
  //             <Button
  //               // TODO improve this - something weird happens with this button overflowing

  //               // fullWidth
  //               width={{ base: 'calc(100vw - 48px)', md: 'calc(100vw - 96px)', lg: '100%' }}
  //               data-testid={SettingsSelectors.UnlockWalletBtn}
  //               disabled={isRunning || !!error}
  //               aria-busy={isRunning}
  //               onClick={submit}
  //               mt={['unset', 'space.05']}
  //               // mx={{ base: 'space.05', md: 'unset' }}
  //             >
  //               Continue
  //             </Button>
  //           </Footer>

  //           {/* </Box> */}
  //         </>
  //       }
  //       /* </DialogContent> */
  //     />
  //   </>
  // );
}
