import { Stack } from 'leather-styles/jsx';
import { styled } from 'leather-styles/jsx';

import { HashDialog } from './hash-dialog';

interface MessageBoxProps {
  message: string;
  hash?: string;
}
export function MessagePreviewBox({ message, hash }: MessageBoxProps) {
  return (
    <Stack
      bg="accent.background-primary"
      border="active"
      borderRadius="sm"
      paddingBottom={hash ? 'space.02' : 0}
    >
      <Stack
        bg="accent.background-primary"
        borderRadius="lg"
        gap="space.02"
        px="space.05"
        py="space.05"
        overflowX="auto"
      >
        {message.split(/\r?\n/).map(line => (
          <styled.span key={line} textStyle="label.01">
            {line}
          </styled.span>
        ))}
      </Stack>
      {hash ? <HashDialog hash={hash} /> : null}
    </Stack>
  );
}
