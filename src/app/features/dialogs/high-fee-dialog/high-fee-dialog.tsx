import { useEffect } from 'react';

import { useDialogs } from '@app/common/hooks/use-dialogs';
import { Dialog } from '@app/ui/components/containers/dialog/dialog';

import { HighFeeConfirmation } from './components/high-fee-confirmation';

export function HighFeeDialog({ learnMoreUrl }: { learnMoreUrl: string }) {
  const { isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation } = useDialogs();

  useEffect(() => {
    return () => {
      if (isShowingHighFeeConfirmation) setIsShowingHighFeeConfirmation(false);
    };
  }, [isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation]);

  return (
    <Dialog isShowing={false} onClose={() => setIsShowingHighFeeConfirmation(false)}>
      {false && <HighFeeConfirmation learnMoreUrl={learnMoreUrl} />}
    </Dialog>
  );
}
