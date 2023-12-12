import { memo } from 'react';

import { styled } from 'leather-styles/jsx';

import { useCreateAccount } from '@app/common/hooks/account/use-create-account';
import { useWalletType } from '@app/common/use-wallet-type';
import { useCurrentAccountIndex } from '@app/store/accounts/account';
import { useFilteredBitcoinAccounts } from '@app/store/accounts/blockchain/bitcoin/bitcoin.ledger';
import { useStacksAccounts } from '@app/store/accounts/blockchain/stacks/stacks-account.hooks';
import { useShowSwitchAccountsState } from '@app/store/ui/ui.hooks';
import { BaseDrawer } from '@app/ui/components/containers/drawer/base-drawer';

import { AccountListUnavailable } from './components/account-list-unavailable';
import { CreateAccountAction } from './components/create-account-action';
import { SwitchAccountList } from './components/switch-account-list';

export const SwitchAccountDrawer = memo(() => {
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

  return (
    <BaseDrawer
      title={<styled.h1 textStyle="heading.05">Select account</styled.h1>} // FIXME this is a hack for Select Account that needs to be fixed
      isShowing={isShowing}
      onClose={onClose}
      footer={whenWallet({
        software: <CreateAccountAction onCreateAccount={onCreateAccount} />,
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
