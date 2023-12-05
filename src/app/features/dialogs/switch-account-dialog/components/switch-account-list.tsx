import { ReactNode, memo } from 'react';
import { Virtuoso } from 'react-virtuoso';

import { css } from 'leather-styles/css';
import { Box } from 'leather-styles/jsx';

import { useWalletType } from '@app/common/use-wallet-type';
import { virtuosoContainerStyle, virtuosoStyle } from '@app/ui/shared/styles/virtuoso-styles';

import { SwitchAccountListItem } from './switch-account-list-item';

interface SwitchAccountListProps {
  handleClose(): void;
  currentAccountIndex: number;
  addressesNum: number;
  footer?: ReactNode;
}
export const SwitchAccountList = memo(
  ({ currentAccountIndex, handleClose, addressesNum }: SwitchAccountListProps) => {
    const { whenWallet } = useWalletType();

    return (
      <Box
        className={css(virtuosoContainerStyle)}
        css={{
          // only allow scroll if more than 6 accounts
          overflowY: addressesNum > 6 ? 'scroll' : 'hidden',
          // fill space on ledger as no create account button
          maxHeight: whenWallet({ ledger: '100vh', software: '' }),
        }}
      >
        <Virtuoso
          useWindowScroll
          className={css(virtuosoStyle)}
          initialTopMostItemIndex={whenWallet({ ledger: 0, software: currentAccountIndex })}
          totalCount={addressesNum}
          itemContent={index => (
            <SwitchAccountListItem
              key={index}
              handleClose={handleClose}
              currentAccountIndex={currentAccountIndex}
              index={index}
            />
          )}
        />
      </Box>
    );
  }
);
