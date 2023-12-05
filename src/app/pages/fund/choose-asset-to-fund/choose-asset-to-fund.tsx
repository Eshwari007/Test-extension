import { useCallback, useMemo } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';

import { AllTransferableCryptoAssetBalances } from '@shared/models/crypto-asset-balance.model';
import { RouteUrls } from '@shared/route-urls';
import { isDefined } from '@shared/utils';

import { useBtcCryptoCurrencyAssetBalance } from '@app/common/hooks/balance/btc/use-btc-crypto-currency-asset-balance';
import { useStxCryptoCurrencyAssetBalance } from '@app/common/hooks/balance/stx/use-stx-crypto-currency-asset-balance';
import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { useWalletType } from '@app/common/use-wallet-type';
import { ChooseAssetContainer } from '@app/components/crypto-assets/choose-crypto-asset/choose-asset-container';
import { ChooseCryptoAssetLayout } from '@app/components/crypto-assets/choose-crypto-asset/choose-crypto-asset.layout';
import { CryptoAssetList } from '@app/components/crypto-assets/choose-crypto-asset/crypto-asset-list';
import { useCheckLedgerBlockchainAvailable } from '@app/store/accounts/blockchain/utils';
import { PageHeader } from '@app/ui/components/containers/headers/page-header';

export function ChooseCryptoAssetToFund() {
  const btcCryptoCurrencyAssetBalance = useBtcCryptoCurrencyAssetBalance();
  const stxCryptoCurrencyAssetBalance = useStxCryptoCurrencyAssetBalance();

  const cryptoCurrencyAssetBalances = useMemo(
    () => [btcCryptoCurrencyAssetBalance, stxCryptoCurrencyAssetBalance],
    [btcCryptoCurrencyAssetBalance, stxCryptoCurrencyAssetBalance]
  );

  const { whenWallet } = useWalletType();
  const navigate = useNavigate();

  const checkBlockchainAvailable = useCheckLedgerBlockchainAvailable();

  const filteredCryptoAssetBalances = useMemo(
    () =>
      cryptoCurrencyAssetBalances.filter(isDefined).filter(assetBalance =>
        whenWallet({
          ledger: checkBlockchainAvailable(assetBalance?.blockchain),
          software: true,
        })
      ),
    [cryptoCurrencyAssetBalances, checkBlockchainAvailable, whenWallet]
  );

  useRouteHeader(<PageHeader onGoBack={() => navigate(RouteUrls.Home)} />);

  const navigateToSendForm = useCallback(
    (cryptoAssetBalance: AllTransferableCryptoAssetBalances) => {
      const { asset } = cryptoAssetBalance;

      const symbol = asset.symbol === '' ? asset.contractAssetName : asset.symbol;
      navigate(RouteUrls.Fund.replace(':currency', symbol.toUpperCase()));
    },
    [navigate]
  );

  return (
    <>
      <ChooseAssetContainer>
        <ChooseCryptoAssetLayout title="choose asset to fund">
          <CryptoAssetList
            onItemClick={navigateToSendForm}
            cryptoAssetBalances={filteredCryptoAssetBalances}
          />
        </ChooseCryptoAssetLayout>
      </ChooseAssetContainer>
      <Outlet />
    </>
  );
}
