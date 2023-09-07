import { useContext } from 'react';

import GenericErrorImg from '@assets/images/generic-error.png';
import { Box, Button, Stack } from 'leather-styles/jsx';

import { useLoading } from '@app/common/hooks/use-loading';
import { delay } from '@app/common/utils';
import { Body } from '@app/components/typography';
import { LedgerTitle } from '@app/features/ledger/components/ledger-title';
import { LedgerWrapper } from '@app/features/ledger/components/ledger-wrapper';

import { ledgerTxSigningContext } from '../ledger-sign-tx.context';

export function ContractPrincipalBugWarning() {
  const { hasUserSkippedBuggyAppWarning } = useContext(ledgerTxSigningContext);
  const { isLoading, setIsLoading, setIsIdle } = useLoading('temp-spinner-deep-link');
  return (
    <LedgerWrapper>
      <Box mb="space.02" mt="space.02">
        <img src={GenericErrorImg} width="106px" />
      </Box>
      <LedgerTitle mt="base-loose">Stacks Ledger app is outdated</LedgerTitle>
      <Body mt="space.04" mx="space.02">
        Some transactions are not compatible with outdated app versions. Update your app in{' '}
        <a href="ledgerlive://manager" style={{ textDecoration: 'underline' }}>
          Ledger Live
        </a>{' '}
        and try again.
      </Body>
      <Stack isInline mb="space.05" mt="space.06">
        <Button
          as="a"
          href="ledgerlive://manager"
          isLoading={isLoading}
          onClick={async () => {
            setIsLoading();
            await delay(300);
            setIsIdle();
          }}
        >
          Open Ledger Live ↗
        </Button>
        <Button
          mode="tertiary"
          onClick={() => hasUserSkippedBuggyAppWarning.done('ignored-warning')}
        >
          Continue anyway
        </Button>
      </Stack>
    </LedgerWrapper>
  );
}
