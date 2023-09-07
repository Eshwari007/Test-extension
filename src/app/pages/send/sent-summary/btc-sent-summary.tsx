import { toast } from 'react-hot-toast';
import { FiCopy, FiExternalLink } from 'react-icons/fi';
import { useLocation } from 'react-router-dom';

// #4164 FIXME migrate useClipboard
import { useClipboard } from '@stacks/ui';
import { Stack } from 'leather-styles/jsx';

import { useAnalytics } from '@app/common/hooks/analytics/use-analytics';
import { useExplorerLink } from '@app/common/hooks/use-explorer-link';
import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { FormAddressDisplayer } from '@app/components/address-displayer/form-address-displayer';
import {
  InfoCard,
  InfoCardAssetValue,
  InfoCardBtn,
  InfoCardFooter,
  InfoCardRow,
  InfoCardSeparator,
} from '@app/components/info-card/info-card';
import { ModalHeader } from '@app/components/modal-header';

import { TxDone } from '../send-crypto-asset-form/components/tx-done';

export function BtcSentSummary() {
  const { state } = useLocation();

  const {
    txId,
    txValue,
    txFiatValue,
    txFiatValueSymbol,
    symbol,
    txLink,
    arrivesIn,
    sendingValue,
    recipient,
    totalSpend,
    feeRowValue,
  } = state;

  const { onCopy } = useClipboard(txId);
  const { handleOpenTxLink } = useExplorerLink();
  const analytics = useAnalytics();

  function onClickLink() {
    void analytics.track('view_transaction_confirmation', { symbol: 'BTC' });
    handleOpenTxLink(txLink);
  }

  function onClickCopy() {
    onCopy();
    toast.success('ID copied!');
  }

  useRouteHeader(<ModalHeader hideActions defaultClose title="Sent" />);

  return (
    <InfoCard>
      <TxDone />
      <InfoCardAssetValue
        value={txValue}
        fiatValue={txFiatValue}
        fiatSymbol={txFiatValueSymbol}
        symbol={symbol}
        px="space.05"
      />

      <Stack width="100%" px="space.06" pb="space.06">
        <InfoCardRow title="To" value={<FormAddressDisplayer address={recipient} />} />
        <InfoCardSeparator />
        <InfoCardRow title="Total spend" value={totalSpend} />

        <InfoCardRow title="Sending" value={sendingValue} />
        <InfoCardRow title="Fee" value={feeRowValue} />
        {arrivesIn && <InfoCardRow title="Arrives in" value={arrivesIn} />}
      </Stack>

      <InfoCardFooter>
        <Stack gap="space.04" isInline width="100%">
          <InfoCardBtn onClick={onClickLink} icon={FiExternalLink} label="View Details" />
          <InfoCardBtn onClick={onClickCopy} icon={FiCopy} label="Copy ID" />
        </Stack>
      </InfoCardFooter>
    </InfoCard>
  );
}
