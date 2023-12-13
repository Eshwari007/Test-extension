import { ReactNode, memo } from 'react';
import { Virtuoso } from 'react-virtuoso';

import { Box } from 'leather-styles/jsx';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
import { useWalletType } from '@app/common/use-wallet-type';

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
    const isAtleastBreakpointMd = useViewportMinWidth('md');

    return (
      <Box
        css={{
          overflowY: 'scroll',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
          // minHeight: 'calc(70vh + 92px)',
          //PETE = probably need to make all drawer-flex base-drawer have this height as otherwise modals don't stretch to bottom
          maxHeight: isAtleastBreakpointMd ? '100%' : '75vh',
        }}
        // minHeight="calc(70vh + 92px)" //set minHeight only on extension
        mb={whenWallet({ ledger: 'space.04', software: '' })}
      >
        <Virtuoso
          useWindowScroll
          // components={{ Header, Footer }}
          initialTopMostItemIndex={whenWallet({ ledger: 0, software: currentAccountIndex })}
          style={{
            paddingTop: '24px',
            // height: isAtleastBreakpointMd ? '100%' : '20vh',
            minHeight: '50vh',
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
