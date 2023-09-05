import { FiEyeOff, FiLock, FiRotateCcw } from 'react-icons/fi';

import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { Box, Stack } from 'leather-styles/jsx';
import { styled } from 'leather-styles/jsx';

import { LeatherButton } from '@app/components/button/button';

interface BackUpSecretKeyLayoutProps {
  onBackedUpSecretKey(): void;
}

export function BackUpSecretKeyActions(props: BackUpSecretKeyLayoutProps): React.JSX.Element {
  const { onBackedUpSecretKey } = props;

  return (
    <>
      <Stack alignItems="center" isInline>
        <FiEyeOff size="12px" />
        <styled.span textStyle="body.02">Your Secret Key gives access to your wallet</styled.span>
      </Stack>
      <Stack alignItems="center" isInline>
        <FiEyeOff size="12px" />
        <styled.span textStyle="body.02">Never share your Secret Key with anyone</styled.span>
      </Stack>
      <Stack alignItems="center" isInline mb="loose">
        <FiLock size="12px" />
        <styled.span textStyle="body.02">Store it somewhere 100% private and secure</styled.span>
      </Stack>

      <LeatherButton
        width="fit-content"
        data-testid={OnboardingSelectors.BackUpSecretKeyBtn}
        onClick={onBackedUpSecretKey}
      >
        I've backed it up
      </LeatherButton>
    </>
  );
}
