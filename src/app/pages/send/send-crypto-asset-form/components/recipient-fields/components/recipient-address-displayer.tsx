import { useCallback } from 'react';
import { FiCopy } from 'react-icons/fi';

import { SendCryptoAssetSelectors } from '@tests/selectors/send.selectors';
import { Box, Text, color, useClipboard } from 'leather-styles/jsx';

import { useAnalytics } from '@app/common/hooks/analytics/use-analytics';
import { SpaceBetween } from '@app/components/layout/space-between';
import { Tooltip } from '@app/components/tooltip';

interface RecipientAddressDisplayerProps {
  address: string;
}
export function RecipientAddressDisplayer({ address }: RecipientAddressDisplayerProps) {
  const analytics = useAnalytics();
  const { onCopy, hasCopied } = useClipboard(address);

  const copyToClipboard = useCallback(() => {
    void analytics.track('copy_recipient_bns_address_to_clipboard');
    onCopy();
  }, [analytics, onCopy]);

  return (
    <SpaceBetween mb="base" width="100%">
      <Text
        color={color('text-caption')}
        data-testid={SendCryptoAssetSelectors.RecipientBnsAddressLabel}
        fontSize={0}
      >
        {address}
      </Text>
      <Tooltip hideOnClick={false} label={hasCopied ? 'Copied!' : 'Copy address'} placement="right">
        <Box
          _hover={{ cursor: 'pointer' }}
          as="button"
          color={color('text-caption')}
          data-testid={SendCryptoAssetSelectors.RecipientBnsAddressCopyToClipboard}
          onClick={copyToClipboard}
          type="button"
        >
          <FiCopy size="16px" />
        </Box>
      </Tooltip>
    </SpaceBetween>
  );
}
