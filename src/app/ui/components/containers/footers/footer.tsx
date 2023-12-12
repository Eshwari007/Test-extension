import { ReactNode } from 'react';

import { Flex } from 'leather-styles/jsx';

interface FooterProps {
  children: ReactNode; // tried HasChildren = Type 'HasChildren' is not assignable to type 'ReactNode'.
}
export function Footer({ children }: FooterProps) {
  return (
    <Flex
      // mt="100px"
      gap="space.05"
      py="space.05"
      px="space.05"
      margin="auto"
      // flexGrow="1"
      // position="fixed" - this position fixed messes up a lot of things
      bottom={0}
      width="100%"
      zIndex={1}
      backgroundColor="accent.background-primary"
      minHeight="92px" // give footer minHeight 92px to help offset vh of virtuoso
      maxWidth="472px" // this is so buggy - set to the same width as base drawer flex - need to fix this properly
      borderRadius={[0, 0, 'lg']}
    >
      {children}
    </Flex>
  );
}
