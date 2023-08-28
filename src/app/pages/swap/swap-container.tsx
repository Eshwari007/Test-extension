import { useCallback, useEffect, useMemo, useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';

import { AlexSDK, Currency, TokenInfo } from 'alex-sdk';
import BigNumber from 'bignumber.js';

import { createMoney } from '@shared/models/money.model';
import { RouteUrls } from '@shared/route-urls';

import { useAllTransferableCryptoAssetBalances } from '@app/common/hooks/use-transferable-asset-balances.hooks';
import { useCurrentAccountStxAddressState } from '@app/store/accounts/blockchain/stacks/stacks-account.hooks';
import { useTransactionBroadcast } from '@app/store/transactions/transaction.hooks';

import { SwapContainerLayout } from './components/swap-container.layout';
import { SwapForm } from './components/swap-form';
import { SwapAsset, SwapFormValues } from './hooks/use-swap';
import { SwapContext, SwapProvider, SwapSubmissionData } from './swap.context';

export function SwapContainer() {
  const alexSDK = useState(() => new AlexSDK())[0];
  const [supportedCurrencies, setSupportedCurrencies] = useState<TokenInfo[]>([]);

  useEffect(() => {
    alexSDK.fetchTokenList().then(tokenList => {
      setSupportedCurrencies(tokenList.filter(t => t.availableInSwap));
    });
  }, []);

  const navigate = useNavigate();

  const allTransferableCryptoAssetBalances = useAllTransferableCryptoAssetBalances();
  const getAssetFromAlexCurrency = useCallback(
    (tokenInfo: TokenInfo): SwapAsset => {
      const currency = tokenInfo.id as Currency;
      if (currency === Currency.STX) {
        const balance = allTransferableCryptoAssetBalances.find(
          x => x.type === 'crypto-currency' && x.blockchain === 'stacks' && x.asset.symbol === 'STX'
        )!.balance;
        return { currency, icon: tokenInfo.icon, name: tokenInfo.name, balance };
      }
      const balance = allTransferableCryptoAssetBalances.find(
        x => x.type === 'fungible-token' && alexSDK.getAddressFrom(currency) === x.asset.contractId
      )?.balance;
      return {
        currency,
        icon: tokenInfo.icon,
        name: tokenInfo.name,
        balance: balance ?? createMoney(0, tokenInfo.name, tokenInfo.decimals),
      };
    },
    [allTransferableCryptoAssetBalances]
  );

  const swappableAssets: SwapAsset[] = useMemo(
    () => supportedCurrencies.map(getAssetFromAlexCurrency),
    [getAssetFromAlexCurrency, supportedCurrencies]
  );

  const [swapSubmissionData, setSwapSubmissionData] = useState<SwapSubmissionData>();
  const [slippage, _setSlippage] = useState(0.04);

  async function onSubmitSwapForReview(values: SwapFormValues) {
    if (values.swapAssetFrom == null || values.swapAssetTo == null) {
      return;
    }
    const [router, lpFee] = await Promise.all([
      alexSDK.getRouter(values.swapAssetFrom.currency, values.swapAssetTo.currency),
      alexSDK.getFeeRate(values.swapAssetFrom.currency, values.swapAssetTo.currency),
    ]);
    setSwapSubmissionData({
      swapAmountFrom: values.swapAmountFrom,
      swapAmountTo: values.swapAmountTo,
      swapAssetFrom: values.swapAssetFrom,
      swapAssetTo: values.swapAssetTo,
      router: router.map(x => getAssetFromAlexCurrency(supportedCurrencies.find(y => y.id === x)!)),
      liquidityFee: new BigNumber(Number(lpFee)).dividedBy(1e8).toNumber(),
      slippage,
    });
    navigate(RouteUrls.SwapReview);
  }

  const stxAddress = useCurrentAccountStxAddressState();
  useTransactionBroadcast();
  function onSubmitSwap() {
    if (swapSubmissionData == null) {
      return;
    }
    const fromAmount = BigInt(
      new BigNumber(swapSubmissionData.swapAmountFrom).multipliedBy(1e8).dp(0).toString()
    );
    const minToAmount = BigInt(
      new BigNumber(swapSubmissionData.swapAmountTo)
        .multipliedBy(1e8)
        .multipliedBy(1 - slippage)
        .dp(0)
        .toString()
    );
    const txToBroadcast = alexSDK.runSwap(
      stxAddress,
      swapSubmissionData.swapAssetFrom.currency,
      swapSubmissionData.swapAssetTo.currency,
      fromAmount,
      minToAmount,
      swapSubmissionData.router.map(x => x.currency)
    );
    // TODO: broadcast the tx
    console.log(txToBroadcast);
    navigate(RouteUrls.SwapSummary);
  }

  async function fetchToAmount(
    from: SwapAsset,
    to: SwapAsset,
    fromAmount: string
  ): Promise<string> {
    const result = await alexSDK.getAmountTo(
      from.currency,
      BigInt(new BigNumber(fromAmount).multipliedBy(1e8).dp(0).toString()),
      to.currency
    );
    return new BigNumber(Number(result)).dividedBy(1e8).toString();
  }
  const swapContextValue: SwapContext = {
    swapSubmissionData,
    fetchToAmount,
    onSubmitSwapForReview,
    onSubmitSwap,
    swappableAssets: swappableAssets,
  };

  return (
    <SwapProvider value={swapContextValue}>
      <SwapContainerLayout>
        <SwapForm>
          <Outlet />
        </SwapForm>
      </SwapContainerLayout>
    </SwapProvider>
  );
}
