import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { Flex, styled } from 'leather-styles/jsx';

import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
import { useThemeSwitcher } from '@app/common/theme-provider';
import { Button } from '@app/ui/components/button/button';
import { LeatherIcon } from '@app/ui/components/icons/leather-icon';
import { LeatherLettermarkIcon } from '@app/ui/components/icons/leather-lettermark-icon';
import { Link } from '@app/ui/components/link/link';

interface WelcomeLayoutProps {
  isGeneratingWallet: boolean;
  onSelectConnectLedger(): void;
  onStartOnboarding(): void;
  onRestoreWallet(): void;
}
export function WelcomeLayout({
  isGeneratingWallet,
  onStartOnboarding,
  onSelectConnectLedger,
  onRestoreWallet,
}: WelcomeLayoutProps): React.JSX.Element {
  const isAtleastBreakpointMd = useViewportMinWidth('md');
  const { theme } = useThemeSwitcher();

  {
    /* FIXME 4370: revisit: this to improve
        - deprecate <Button invert
        - setting all these custom colors etc. 
        - also losing hover styles etc. so not a good approach really = check with design for a custom solution to this
        - could be simpler using different components and hideOnSm etc 
    */
  }
  const tagline = 'Bitcoin for the rest of us';
  const taglineExtended = 'The bitcoin wallet for the rest of us';
  const subheader =
    'Leather is the only Bitcoin wallet you need to tap into the emerging Bitcoin economy';

  return (
    <Flex flexDir={{ base: 'column-reverse', md: 'row' }} minW="100vw" minH="100vh">
      <Flex
        flexDir="column"
        bg={{ base: 'ink.1', md: 'ink.12' }}
        flex={{ base: 1, md: 2 }}
        p="space.05"
      >
        <Flex
          flexDir="column"
          flex={[1, 1, 0]}
          justifyContent={{ base: 'end', md: 'flex-start' }}
          color={{ base: 'ink.12', md: 'ink.2' }}
        >
          <styled.h1 hideBelow="md" textStyle="display.01" maxWidth="880px">
            {tagline}
          </styled.h1>
          <styled.h1 hideFrom="md" textStyle="heading.03" maxWidth="880px">
            {taglineExtended}
          </styled.h1>

          <styled.h2
            textStyle={['label.01', '', 'heading.04']}
            mt={['space.02', '', 'space.07']}
            maxW="556px"
          >
            {subheader}
          </styled.h2>
        </Flex>
        <Flex flexDir={{ base: 'column', md: 'row' }} gap="space.05" mt="space.07">
          <Button
            onClick={onStartOnboarding}
            data-testid={OnboardingSelectors.SignUpBtn}
            aria-busy={isGeneratingWallet}
            justifyContent="center"
            alignItems="center"
            gap="space.02"
            px="space.04"
            py="space.02"
            bg={{
              base: theme === 'light' ? 'darkModeInk.12' : 'lightModeInk.1',
              md: theme === 'light' ? 'lightModeInk.1' : 'lightModeInk.12',
            }}
            color={{
              base: theme === 'light' ? 'lightModeInk.12' : 'darkModeInk.1',
              md: theme === 'light' ? 'darkModeInk.1' : 'lightModeInk.1',
            }}
          >
            Create new wallet
          </Button>

          <Flex gap="space.05" alignItems="flex-start">
            <Link
              paddingTop="space.02"
              paddingBottom={{ base: 'space.02', md: 'unset' }}
              bg={{ base: 'darkModeInk.1', md: 'inherit' }}
              color={{
                base: 'lightModeInk.1',
                md: theme === 'light' ? 'darkModeInk.12' : 'lightModeInk.12',
              }}
              border={{ base: '1px solid currentColor', md: 'unset' }}
              flex={1}
              minWidth="122px" // TODO 4370 check whats happening here and if it's needed now this is Link
              data-testid={OnboardingSelectors.SignInLink}
              onClick={onRestoreWallet}
              size="lg"
            >
              Use existing key
            </Link>
            <Link
              paddingTop="space.02"
              paddingBottom={{ base: 'space.02', md: 'unset' }}
              bg={{ base: 'darkModeInk.1', md: 'unset' }}
              color={{
                base: 'lightModeInk.1',
                md: theme === 'light' ? 'darkModeInk.12' : 'lightModeInk.12',
              }}
              // color="darkModeInk.12"
              border={{ base: '1px solid currentColor', md: 'unset' }}
              flex={1}
              minWidth="88px"
              onClick={onSelectConnectLedger}
              size="lg"
            >
              Use Ledger
            </Link>
            <Button
              hideFrom="md"
              variant="outline"
              invert={isAtleastBreakpointMd}
              flex={1}
              mt={[0, 0, 'space.05']}
            >
              Use Ledger
            </Button>
          </Flex>
        </Flex>
      </Flex>
      <Flex
        p="space.05"
        //  TODO 4370 revisit this with new colours
        // bg="ink.2"
        // color="ink.12"
        bg={{ base: 'darkModeInk.1', md: 'accent.background-primary' }}
        color={{ base: 'lightModeInk.1', md: 'ink.12' }}
        flexDir="column"
        justifyContent="space-between"
        flex={{ base: '', md: 1 }}
      >
        <Flex justifyContent="space-between">
          <LeatherIcon width="150px" height="34px" />
          <Link href="https://leather.io/">leather.io</Link>
        </Flex>
        <LeatherLettermarkIcon hideBelow="md" width="100%" />
      </Flex>
    </Flex>
  );
}
