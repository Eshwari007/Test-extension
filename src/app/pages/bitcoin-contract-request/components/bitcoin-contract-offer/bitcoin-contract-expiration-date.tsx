import { Flex } from 'leather-styles/jsx';

import { Text } from '@app/components/typography';

interface BitcoinContractExpirationDateProps {
  expirationDate: string;
}
export function BitcoinContractExpirationDate({
  expirationDate,
}: BitcoinContractExpirationDateProps) {
  return (
    <Flex p="space.05" gap="space.05" width="100%" justifyContent="space-between">
      <styled.span fontSize={2} fontWeight="bold">
        Expiration Date
      </styled.span>
      <styled.span fontSize={2}>{expirationDate}</styled.span>
    </Flex>
  );
}
