import { ReactNode, memo, useEffect, useRef } from 'react';
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
    // PETE - this is pretty close now but the Create new account has a bit too much space below
    // great progress though! that part can be solved by footers
    // next test all flows to make sure they mostly look OK

    //     tried these headers and footers but then bottom footer not setGlobalAnalyticsKey
    //     I think its close enough now with a bit more testing

    // just make sure it looks good in extension

    // const Header = () => 'Select Account';
    // const Footer = () => <CreateAccountAction onCreateAccount={() => null} />;
    // const virtuoso = useRef(null);
    // console.log('currentAccountIndex sw', currentAccountIndex);
    // useEffect(
    //   () =>
    //     virtuoso.current.scrollToIndex({
    //       index: currentAccountIndex,
    //     }),
    //   [virtuoso, currentAccountIndex]
    // );

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
