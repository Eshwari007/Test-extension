import { memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Virtuoso } from 'react-virtuoso';

import { css } from 'leather-styles/css';
import { Box } from 'leather-styles/jsx';

import { useFilteredBitcoinAccounts } from '@app/store/accounts/blockchain/bitcoin/bitcoin.ledger';
import { useStacksAccounts } from '@app/store/accounts/blockchain/stacks/stacks-account.hooks';
import { Dialog } from '@app/ui/components/containers/dialog/dialog';
import { virtuosoContainerStyle, virtuosoStyle } from '@app/ui/shared/styles/virtuoso-styles';

import { AccountListItem } from './account-list-item';

// TODO 4370 -   should this move to other dialogs in features/dialogs?
export const RecipientAccountsDialog = memo(() => {
  const stacksAccounts = useStacksAccounts();
  const navigate = useNavigate();

  const onGoBack = useCallback(() => navigate('..', { replace: true }), [navigate]);
  const bitcoinAccounts = useFilteredBitcoinAccounts();
  const btcAddressesNum = bitcoinAccounts.length / 2;
  const stacksAddressesNum = stacksAccounts.length;

  if (stacksAddressesNum === 0 && btcAddressesNum === 0) return null;

  // TODO 4370 - test UI of this and other virtuoso lists and maybe change to share more code?
  return (
    <Dialog title="My accounts" isShowing onClose={onGoBack}>
      <Box
        className={css(virtuosoContainerStyle)}
        css={{
          // only allow scroll if more than 7 accounts
          overflowY: stacksAccounts.length > 7 ? 'scroll' : 'hidden',
          maxHeight: '100vh',
        }}
      >
        <Virtuoso
          className={css(virtuosoStyle)}
          itemContent={index => (
            <AccountListItem
              key={index}
              stacksAccount={stacksAccounts[index]}
              onClose={onGoBack}
              index={index}
            />
          )}
          totalCount={stacksAddressesNum || btcAddressesNum}
        />
      </Box>
    </Dialog>
  );
});
