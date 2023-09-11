import { ReactNode, useMemo } from 'react';

import { deserializeTransaction } from '@stacks/transactions';
import { Stack } from 'leather-styles/jsx';

import { SubmittedTransactionItem } from '@app/features/activity-list/components/submitted-transaction-list/submitted-transaction-item';
import { SubmittedTransaction } from '@app/store/submitted-transactions/submitted-transactions.slice';

type SubmittedTransactionListItemProps = SubmittedTransaction;

export function SubmittedTransactionListItem({ rawTx, txId }: SubmittedTransactionListItemProps) {
  const submittedTx = useMemo(() => deserializeTransaction(rawTx), [rawTx]);
  return <SubmittedTransactionItem transaction={submittedTx} txId={txId} />;
}

interface SubmittedTransactionListLayoutProps {
  children: ReactNode;
}
export function SubmittedTransactionListLayout({ children }: SubmittedTransactionListLayoutProps) {
  return (
    <>
      <styled.span textStyle="body.small" color={token('colors.accent.text-subdued')}>
        Submitted
      </styled.span>
      <Stack mt="base-loose" pb="extra-loose" gap="loose">
        {children}
      </Stack>
    </>
  );
}
