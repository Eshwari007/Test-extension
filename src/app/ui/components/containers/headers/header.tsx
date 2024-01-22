import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
// import { SettingsSelectors } from '@tests/selectors/settings.selectors';
import { Flex, HStack, styled } from 'leather-styles/jsx';

// import { Button } from '@app/ui/components/button/button';
import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { CloseIcon } from '@app/ui/components/icons/close-icon';
import { HamburgerIcon } from '@app/ui/components/icons/hamburger-icon';
import { LeatherLogo } from '@app/ui/components/leather-logo';

// import { useHover } from 'use-events';
import { DropdownMenu } from '../../dowpdown-menu/dropdown-menu';
import { NetworkModeBadge } from './components/network-mode-badge';
import { HeaderActionButton } from './header-action-button';

// FIXME 4370 task #2 - finish global header replacement
//  - ideally this header will be more DUMB
// - no knowledge of router - RouteUrls / useNavigate
// - no state needed for Testnet
// - using panda css instead of hover events

// can't use navigate in here to make logo go to home. Need to pass that in from Container -> Page, same as Testnet I guess

// Ledger:
// seems to be the only thing using enableGoBack, waitingOnPerformedActionMessage, isWaitingOnPerformedAction
// waitingOnPerformedActionMessage is always hardcoded as "Ledger device in use"
// we use hover events to show isWaitingOnPerformedAction sometimes but only when hovering on the title?

/*

-  Need to allow for account selection? In place of Logo? - is that used yet
- need to allow for signature pages - show account at end 
- look into type narrowing for different variants
*/

/**
 */
export interface HeaderProps {
  variant: 'home' | 'page' | 'onboarding' | 'big-title';
  enableGoBack?: boolean; // seems this is needed in ledger and sendInscription. Would be good to merge it and onGoBack
  isWaitingOnPerformedAction?: boolean; // seems this is needed for ledger - change it to ledgerAction?
  onClose?(): void;
  onGoBack?(): void;
  title?: string;
  // waitingOnPerformedActionMessage?: string;
}

/** In figma there is a few headers, ALL seem very similar but with slight variants:
  - Full page:
      - home - BG --Accent-background-primary, logo, network, menu - can't close
      - page - BG Accent-background-secondary, logo, network, menu, can close - X on right
      - onboarding  - BG Accent-background-secondary,logo can go back <- on left, no network or menu
  - Approval / PSBT have unanswered Qs and may need more work  
  */
export function Header({
  variant = 'page',
  enableGoBack,
  isWaitingOnPerformedAction,
  onClose,
  onGoBack, // title,
  // waitingOnPerformedActionMessage, // seems ledger needs this and it's always hardcoded as "Ledger device in use"
  title, // should make this a consistent string and also have an option for bigTitle? a different variant perhaps?
}: HeaderProps) {
  // FIXME - in oldHeader - clicking settings is controlled by state hooks? Weird.
  // need to get new settings menu in place and check this and possibly stop using jotai

  // useDialogs is the old useDrawers but why does the SettingsMenu button interaction belong there?
  // const { isShowingSettings, setIsShowingSettings } = useDialogs();

  if (variant === 'big-title') {
    return (
      <styled.header p="space.05">
        <Flex width="100%" justifyContent="space-between">
          <styled.h1 textStyle="heading.03" maxWidth="270px">
            {title}
          </styled.h1>
          {onClose && <HeaderActionButton icon={<CloseIcon />} onAction={onClose} />}
        </Flex>
      </styled.header>
    );
  }

  return (
    <styled.header
      px={{ base: 'space.04', md: 'space.07' }}
      py={{ base: 'space.04', md: 'space.05' }}
      bgColor={variant === 'home' ? 'accent.background-primary' : 'accent.background-secondary'}
    >
      <Flex
        width="100%"
        maxWidth={{ base: '392px', md: '882px' }}
        verticalAlign="middle"
        justifyContent="space-between"
        margin={{ base: 0, md: 'auto' }}
      >
        <Flex>
          {variant !== 'home' && (enableGoBack || onGoBack) ? (
            <HeaderActionButton
              icon={<ArrowLeftIcon />}
              isWaitingOnPerformedAction={isWaitingOnPerformedAction}
              onAction={onGoBack} // SMELL this needs to be cleaned as what if no onGoBack but enableGoBack?
            />
          ) : undefined}
          <LeatherLogo
            data-testid={OnboardingSelectors.LeatherLogoRouteToHome}
            // 4370 TODO - asess if we need these other props
            // width="72px"
            // verticalAlign="middle"
            // onClick={variant !== 'home' ? () => navigate(RouteUrls.Home) : undefined}
          />
        </Flex>

        {title && (
          // Check this as Select account was : <styled.h1 textStyle="heading.05">Select account</styled.h1>
          <styled.span alignSelf="center" flexBasis="60%" textAlign="center" textStyle="heading.05">
            {title}
          </styled.span>
        )}
        <HStack alignItems="center" flexBasis="20%" justifyContent="flex-end">
          {/* // FIXME 4370 task #6 - network mode relies on accessing state so fails on Storybook  */}
          <NetworkModeBadge isTestnetChain name="Testnet" onClick={() => null} />
          {variant !== 'onboarding' && (
            <>
              {/* <Button
                data-testid={SettingsSelectors.SettingsMenuBtn}
                // FIXME 4370 task #6 - need to make this settings menu clickable here
                // onClick={() => setIsShowingSettings(!isShowingSettings)}
                onClick={() => null}
                variant="ghost"
              >
                <HamburgerIcon />
              </Button> */}
              <DropdownMenu.Root>
                <DropdownMenu.Trigger>
                  <HamburgerIcon />
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content>
                    <DropdownMenu.Group>
                      <DropdownMenu.Item>Some setting</DropdownMenu.Item>
                    </DropdownMenu.Group>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </>
          )}
          {variant === 'page' && onClose && (
            <HeaderActionButton
              icon={<CloseIcon />}
              isWaitingOnPerformedAction={isWaitingOnPerformedAction}
              onAction={onClose}
            />
          )}
        </HStack>
      </Flex>
    </styled.header>
  );
}
