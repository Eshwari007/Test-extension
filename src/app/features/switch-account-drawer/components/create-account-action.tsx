import { Flex } from 'leather-styles/jsx';

import { LeatherButton } from '@app/ui/components/button';

interface CreateAccountActionProps {
  onCreateAccount(): void;
}
export function CreateAccountAction({ onCreateAccount }: CreateAccountActionProps) {
  return (
    <Flex
      // mt="100px"
      py="space.05"
      px="space.05"
      margin="auto"
      // flexGrow="1"
      // position="fixed" - this position fixed fucks up a lot of things
      bottom={0}
      width="100%"
      zIndex={1}
      backgroundColor="accent.background-primary"
      minHeight="92px" // give footer minHeight 92px to help offset vh of virtuoso
      maxWidth="472px" // this is so buggy - set to the same width as base drawer flex - need to fix this properly
    >
      <LeatherButton fullWidth onClick={() => onCreateAccount()}>
        Create new account
      </LeatherButton>
    </Flex>
  );
}
