import { useEffect } from 'react';
import { FiAlertTriangle } from 'react-icons/fi';

import { Box } from 'leather-styles/jsx';

import { useDrawers } from '@app/common/hooks/use-drawers';
import { ControlledDrawer } from '@app/components/drawer/controlled-drawer';

import { HighFeeConfirmation } from './components/high-fee-confirmation';

export function HighFeeDrawer(props: { learnMoreUrl: string }) {
  const { learnMoreUrl } = props;
  const { isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation } = useDrawers();

  useEffect(() => {
    return () => {
      if (isShowingHighFeeConfirmation) setIsShowingHighFeeConfirmation(false);
    };
  }, [isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation]);

  return (
    <ControlledDrawer
      icon={<Box as={FiAlertTriangle} color={token('colors.error')} size="36px" />}
      isShowing={isShowingHighFeeConfirmation}
      onClose={() => setIsShowingHighFeeConfirmation(false)}
    >
      {isShowingHighFeeConfirmation && <HighFeeConfirmation learnMoreUrl={learnMoreUrl} />}
    </ControlledDrawer>
  );
}
