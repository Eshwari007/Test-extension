import React from 'react';

import { toRelativeTime } from '@common/utils';
import type { ContractCallTransaction } from '@stacks/stacks-blockchain-api-types';
import { Box, Flex, styled } from 'leather-styles/jsx';

interface TxCardProps {
  tx: ContractCallTransaction;
  label: string;
}
export const TxCard: React.FC<TxCardProps> = ({ tx, label }) => {
  const addr = tx.sender_address;
  const shortAddr = `${addr.slice(0, 5)}...${addr.slice(addr.length - 6, addr.length - 1)}`;
  return (
    <Box
      flex="0 1 280px"
      mr="10px"
      mt={3}
      borderColor="#F0F0F5"
      borderWidth="1px"
      borderRadius="12px"
      p={6}
      _hover={{
        borderColor: 'ink.400',
        cursor: 'pointer',
      }}
      onClick={() => {
        const url = `https://testnet-explorer.blockstack.org/txid/${tx.tx_id}`;
        window.open(url, '_blank');
      }}
    >
      <Flex>
        <Box>
          <styled.span color="ink.600">{shortAddr}</styled.span>
        </Box>
        <Box flexGrow={1} textAlign="right">
          <styled.span color="ink.600">{toRelativeTime(tx.burn_block_time * 1000)}</styled.span>
        </Box>
      </Flex>
      <styled.span display="block" textStyle="body.large" mt={3}>
        {label}
      </styled.span>
    </Box>
  );
};
