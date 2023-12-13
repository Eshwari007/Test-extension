import { memo } from 'react';

import { styled } from 'leather-styles/jsx';

import { useCreateAccount } from '@app/common/hooks/account/use-create-account';
import { useWalletType } from '@app/common/use-wallet-type';
import { useCurrentAccountIndex } from '@app/store/accounts/account';
import { useFilteredBitcoinAccounts } from '@app/store/accounts/blockchain/bitcoin/bitcoin.ledger';
import { useStacksAccounts } from '@app/store/accounts/blockchain/stacks/stacks-account.hooks';
import { useShowSwitchAccountsState } from '@app/store/ui/ui.hooks';
import { LeatherButton } from '@app/ui/components/button';
import { BaseDrawer } from '@app/ui/components/containers/drawer/base-drawer';

import { AccountListUnavailable } from './components/account-list-unavailable';
import { SwitchAccountList } from './components/switch-account-list';

export const SwitchAccountDrawer = memo(() => {
  //TODO - see if I can get rid of this jotai stuff
  const [isShowing, setShowSwitchAccountsState] = useShowSwitchAccountsState();

  const currentAccountIndex = useCurrentAccountIndex();
  const createAccount = useCreateAccount();
  const { whenWallet } = useWalletType();

  const stacksAccounts = useStacksAccounts();
  const bitcoinAccounts = useFilteredBitcoinAccounts();
  const btcAddressesNum = bitcoinAccounts.length / 2;
  const stacksAddressesNum = stacksAccounts.length;

  const onClose = () => setShowSwitchAccountsState(false);

  const onCreateAccount = () => {
    createAccount();
    setShowSwitchAccountsState(false);
  };

  if (isShowing && stacksAddressesNum === 0 && btcAddressesNum === 0) {
    return <AccountListUnavailable />;
  }
  console.log('currentAccountIndex', currentAccountIndex);

  // without this early return it crashes on new install with:
  // Wallet is neither of type `ledger` nor `software`
  if (!isShowing) return null;
  // FIXME - how is this even getting loaded at all on install?!?!?!

  return (
    <BaseDrawer
      title={<styled.h1 textStyle="heading.05">Select account</styled.h1>} // FIXME this is a hack for Select Account that needs to be fixed
      isShowing={isShowing}
      onClose={onClose}
      footer={whenWallet({
        software: (
          <LeatherButton fullWidth onClick={() => onCreateAccount()}>
            Create new account
          </LeatherButton>
        ),
        ledger: <></>,
      })}
    >
      <SwitchAccountList
        currentAccountIndex={currentAccountIndex}
        handleClose={onClose}
        addressesNum={stacksAddressesNum || btcAddressesNum}
      />
    </BaseDrawer>
  );
});
