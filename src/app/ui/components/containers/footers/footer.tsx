import { Flex } from 'leather-styles/jsx';

import { HasChildren } from '@app/common/has-children';

/** Footer is only used at smaller widths - in Dialog / Page card view / extension size */
export function Footer({ children }: HasChildren) {
  return (
    <Flex
      gap="space.05"
      py="space.05"
      px="space.05"
      // Taken from request Password to avoud extending FlexProps here and polluting docs
      // px="space.00"
      // px={{ base: 'space.00', md: 'space.05' }}
      margin="auto"
      bottom={0}
      left={0} // nneds this for small size fixed
      width="100%"
      zIndex={1} // 999 in FormFooter - check it's OK
      backgroundColor="accent.background-primary"
      minHeight="92px"
      // == test this - max-width restricts us in Send flows for example .
      //
      // maxWidth={{ base: '100vw', md: '450px' }}
      // changing this for new lock screen. Make sure it looks OK on others i.e. all one column layouts
      // maxWidth={{ base: '100vw', md: '100vw' }}
      borderRadius={[0, 0, 'lg']}
      position={{ base: 'fixed', md: 'sticky' }}
    >
      {/* seem to need this always apart from password/ ReceiveTokensFooter / signout - probably good to always have it */}
      <Flex flexDirection="column" width="100%" gap="space.04">
        {children}
      </Flex>
    </Flex>
  );
}
