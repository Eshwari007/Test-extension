import { useLocation, useNavigate } from 'react-router-dom';

import { BitcoinTx } from '@shared/models/transactions/bitcoin-transaction.model';
import { RouteUrls } from '@shared/route-urls';

import { useLocationStateWithCache } from '@app/common/hooks/use-location-state';

import { IncreaseBtcFeeForm } from './components/increase-btc-fee-form';
import { IncreaseFeeDialog } from './increase-fee-dialog';

function useIncreaseBtcFeeDialogState() {
  return {
    tx: useLocationStateWithCache('btcTx') as BitcoinTx,
  };
}

export function IncreaseBtcFeeDialog() {
  const { tx } = useIncreaseBtcFeeDialogState();
  const navigate = useNavigate();
  const location = useLocation();

  const onClose = () => {
    navigate(RouteUrls.Home);
  };

  if (!tx) return null;

  return (
    <IncreaseFeeDialog
      feeForm={<IncreaseBtcFeeForm btcTx={tx} />}
      onClose={onClose}
      isShowing={location.pathname === RouteUrls.IncreaseBtcFee}
    />
  );
}
