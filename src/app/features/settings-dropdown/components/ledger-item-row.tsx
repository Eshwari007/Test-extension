import { Flex, Text } from 'leather-styles/jsx';
import { Divider } from 'leather-styles/jsx';

import { WalletTypeLedgerIcon } from '@app/components/icons/wallet-type-ledger-icon';

interface LedgerDeviceItemRowProps {
  deviceType?: string;
}
export function LedgerDeviceItemRow({ deviceType }: LedgerDeviceItemRowProps) {
  return (
    <>
      <Flex my="base-tight" mb="base" mx="base" fontSize="14px" alignItems="center">
        <WalletTypeLedgerIcon mr="base-tight" />
        <Text color={color('text-body')} cursor="default">
          Ledger {deviceType ?? ''}
        </Text>
      </Flex>
      <Divider />
    </>
  );
}
