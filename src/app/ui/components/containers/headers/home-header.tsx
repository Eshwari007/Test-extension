import { useNavigate } from 'react-router-dom';

import { OnboardingSelectors } from '@tests/selectors/onboarding.selectors';
import { SettingsSelectors } from '@tests/selectors/settings.selectors';
import { Flex, FlexProps, HStack, styled } from 'leather-styles/jsx';

import { RouteUrls } from '@shared/route-urls';

import { useDialogs } from '@app/common/hooks/use-dialogs';
import { useViewportMinWidth } from '@app/common/hooks/use-media-query';
import { AppVersion } from '@app/components/app-version';
import { NetworkModeBadge } from '@app/components/network-mode-badge';
import { Button } from '@app/ui/components/button/button';
import { HOME_MAX_WIDTH } from '@app/ui/components/containers/home.layout';
import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { HamburgerIcon } from '@app/ui/components/icons/hamburger-icon';
import { LeatherLogo } from '@app/ui/components/leather-logo';

interface HomeHeaderProps extends FlexProps {
  onClose?(): void;
  title?: string;
}
/** @deprecated */
export function HomeHeader(props: HomeHeaderProps) {
  const { onClose, title } = props;
  const { isShowingSettings, setIsShowingSettings } = useDialogs();
  const navigate = useNavigate();

  const isBreakpointSm = useViewportMinWidth('sm');

  return (
    <Flex
      // alignItems={hideSettings ? 'center' : 'flex-start'}
      backgroundColor={['accent.background-primary', 'accent.background-secondary']}
      justifyContent="space-between"
      minHeight={['unset', '80px']}
      p="space.04"
      position="relative"
      maxWidth={HOME_MAX_WIDTH}
      width="100%"
      margin="auto"
    >
      {/* back button */}
      {onClose ? (
        <Flex flexBasis="20%">
          <Button onClick={onClose} variant="ghost">
            <ArrowLeftIcon />
          </Button>
        </Flex>
      ) : null}

      {/*  TODO try to use panda responsive style not a hook */}
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
              onClick={() => navigate(RouteUrls.Home)}
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
        {/* TODO this should go with new header */}
        {/* {!hideSettings && ( */}
        <Button
          data-testid={SettingsSelectors.SettingsMenuBtn}
          onClick={() => setIsShowingSettings(!isShowingSettings)}
          variant="ghost"
        >
          <HamburgerIcon />
        </Button>
        {/* )} */}
      </HStack>
    </Flex>
  );
}
