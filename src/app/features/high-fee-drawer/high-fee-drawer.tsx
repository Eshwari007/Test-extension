import { useEffect } from 'react';

import { useDrawers } from '@app/common/hooks/use-drawers';
import { BaseDrawer } from '@app/ui/components/containers/drawer/base-drawer';

// import { ErrorIcon } from '@app/ui/components/icons/error-icon';
import { HighFeeConfirmation } from './components/high-fee-confirmation';

export function HighFeeDrawer({ learnMoreUrl }: { learnMoreUrl: string }) {
  const { isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation } = useDrawers();

  useEffect(() => {
    return () => {
      if (isShowingHighFeeConfirmation) setIsShowingHighFeeConfirmation(false);
    };
  }, [isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation]);

  return (
    <BaseDrawer
      // TODO - see if we can remove this - only place using this icon slot
      // icon={<ErrorIcon color="error.label" size="xl" />}
      // figure out how this works in general
      isShowing={isShowingHighFeeConfirmation}
      onClose={() => setIsShowingHighFeeConfirmation(false)}
    >
      {isShowingHighFeeConfirmation && <HighFeeConfirmation learnMoreUrl={learnMoreUrl} />}
    </BaseDrawer>
  );
}
