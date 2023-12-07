import { memo } from 'react';
import { Virtuoso } from 'react-virtuoso';

import { Box } from 'leather-styles/jsx';

import { useWalletType } from '@app/common/use-wallet-type';

import { SwitchAccountListItem } from './switch-account-list-item';

interface SwitchAccountListProps {
  handleClose(): void;
  currentAccountIndex: number;
  addressesNum: number;
}
export const SwitchAccountList = memo(
  ({ currentAccountIndex, handleClose, addressesNum }: SwitchAccountListProps) => {
    const { whenWallet } = useWalletType();
    // PETE - this is pretty close now but the Create new account has a bit too much space below
    // great progress though! that part can be solved by footers
    // next test all flows to make sure they mostly look OK

    return (
      <Box
        css={{
          overflowY: 'scroll',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        }}
        minHeight="calc(70vh + 92px)" //set minHeight only on extension
      >
        <Virtuoso
          initialTopMostItemIndex={whenWallet({ ledger: 0, software: currentAccountIndex })}
          style={{
            paddingTop: '24px',
            height: '70vh',
          }}
          totalCount={addressesNum}
          itemContent={index => (
            <Box mx={['space.05', 'space.06']} key={index}>
              <SwitchAccountListItem
                handleClose={handleClose}
                currentAccountIndex={currentAccountIndex}
                index={index}
              />
            </Box>
          )}
        />
      </Box>
    );
  }
);
