import { memo } from 'react';

import { useCreateAccount } from '@app/common/hooks/account/use-create-account';
import { useWalletType } from '@app/common/use-wallet-type';
import { useCurrentAccountIndex } from '@app/store/accounts/account';
import { useFilteredBitcoinAccounts } from '@app/store/accounts/blockchain/bitcoin/bitcoin.ledger';
import { useStacksAccounts } from '@app/store/accounts/blockchain/stacks/stacks-account.hooks';
import { useShowSwitchAccountsState } from '@app/store/ui/ui.hooks';
import { Button } from '@app/ui/components/button/button';
import { Dialog } from '@app/ui/components/containers/dialog/dialog';
import { Footer } from '@app/ui/components/containers/footers/footer';

import { AccountListUnavailable } from './components/account-list-unavailable';
import { SwitchAccountList } from './components/switch-account-list';

export const SwitchAccountDialog = memo(() => {
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

  // #4370 SMELL without this early return the wallet crashes on new install with: Wallet is neither of type `ledger` nor `software`
  // FIXME - this shouldn't be rendered until necessary
  if (!isShowing) return null;

  return (
    <Dialog
      title="Select account"
      isShowing={isShowing}
      onClose={onClose}
      footer={whenWallet({
        software: (
          <Footer>
            <Button fullWidth onClick={() => onCreateAccount()}>
              Create new account
            </Button>
          </Footer>
        ),
        ledger: <></>,
      })}
    >
      <SwitchAccountList
        currentAccountIndex={currentAccountIndex}
        handleClose={onClose}
        addressesNum={stacksAddressesNum || btcAddressesNum}
      />
    </Dialog>
  );
});
