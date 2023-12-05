import { useLocation, useNavigate } from 'react-router-dom';

import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { SettingsSelectors } from '@tests/selectors/settings.selectors';
import { Flex, FlexProps, HStack, styled } from 'leather-styles/jsx';

import { RouteUrls } from '@shared/route-urls';

import { useDrawers } from '@app/common/hooks/use-drawers';
import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
import { NetworkModeBadge } from '@app/components/network-mode-badge';
import { LeatherButton } from '@app/ui/components/button';
import { LeatherLogo } from '@app/ui/components/containers/leather-logo';
import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { HamburgerIcon } from '@app/ui/components/icons/hamburger-icon';

import { AppVersion } from '../../../components/app-version';

function isSettingsClickable(pathname: RouteUrls) {
  return (
    pathname !== RouteUrls.RequestDiagnostics &&
    pathname !== RouteUrls.Onboarding &&
    pathname !== RouteUrls.BackUpSecretKey &&
    pathname !== RouteUrls.SetPassword &&
    pathname !== RouteUrls.SignIn
  );
}

function isLeatherLogoClickable(pathname: RouteUrls) {
  return (
    isSettingsClickable(pathname) && pathname !== RouteUrls.Home // should be able to click logo on home
  );
}

// Seems important. This is the main home header
interface HeaderProps extends FlexProps {
  onClose?(): void;
  title?: string;
}
export function Header(props: HeaderProps) {
  const { onClose, title } = props;
  const { isShowingSettings, setIsShowingSettings } = useDrawers();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const isBreakpointSm = useViewportMinWidth('sm');

  const hideSettings = !isSettingsClickable(pathname as RouteUrls);

  return (
    <Flex
      alignItems={hideSettings ? 'center' : 'flex-start'} // try get rid of this
      backgroundColor={['accent.background-primary', 'accent.background-secondary']}
      justifyContent="space-between"
      minHeight={['unset', '80px']}
      p="space.04"
      position="relative"
    >
      {/* back button */}
      {onClose ? (
        <Flex flexBasis="20%">
          <LeatherButton onClick={onClose} variant="ghost">
            <ArrowLeftIcon />
          </LeatherButton>
        </Flex>
      ) : null}

      {/* Extension mode?  */}
      {!title && (!onClose || isBreakpointSm) ? (
        <Flex
          alignItems="center"
          flexBasis="60%"
          height="32px"
          justifyContent={onClose ? 'center' : 'unset'}
          width="100%"
        >
          <HStack alignItems="flex-end" gap="space.01">
            <LeatherLogo
              data-testid={OnboardingSelectors.LeatherLogoRouteToHome}
              onClick={
                isLeatherLogoClickable(pathname as RouteUrls)
                  ? () => navigate(RouteUrls.Home)
                  : undefined
              }
            />
            <AppVersion />
          </HStack>
        </Flex>
      ) : (
        <styled.span alignSelf="center" flexBasis="60%" textAlign="center" textStyle="heading.05">
          {title}
        </styled.span>
      )}
      <HStack alignItems="center" flexBasis="20%" justifyContent="flex-end">
        <NetworkModeBadge />
        {!hideSettings && (
          <LeatherButton
            data-testid={SettingsSelectors.SettingsMenuBtn}
            onClick={() => setIsShowingSettings(!isShowingSettings)}
            variant="ghost"
          >
            <HamburgerIcon />
          </LeatherButton>
        )}
      </HStack>
    </Flex>
  );
}
