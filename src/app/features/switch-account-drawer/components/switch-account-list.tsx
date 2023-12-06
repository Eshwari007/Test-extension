import { memo } from 'react';
import { Virtuoso } from 'react-virtuoso';

import { Box } from 'leather-styles/jsx';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
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
    const isAtleastBreakpointMd = useViewportMinWidth('md');

    return (
      <Box
        css={{
          overflowY: 'scroll',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        }}
        minHeight={isAtleastBreakpointMd ? 'calc(70vh + 92px)' : 'calc(70vh + 92px)'}
      >
        <Virtuoso
          initialTopMostItemIndex={whenWallet({ ledger: 0, software: currentAccountIndex })}
          // height="72px"
          // style={{ paddingTop: '24px', height: '70vh' }}
          style={{
            paddingTop: '24px',
            height: isAtleastBreakpointMd ? '70vh' : '90vh',
            // overflowY: 'scroll',
          }} //change 40vh back to 90vh after testing Create new
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
