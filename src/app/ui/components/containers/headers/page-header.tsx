import { useNavigate } from 'react-router-dom';

import { SharedComponentsSelectors } from '@tests/selectors/shared-component.selectors';
import { Box, Flex, styled } from 'leather-styles/jsx';

import { RouteUrls } from '@shared/route-urls';

import { NetworkModeBadge } from '@app/components/network-mode-badge';
import { Button } from '@app/ui/components/button/button';
import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { CloseIcon } from '@app/ui/components/icons/close-icon';

// #4370 TODO - refactor headers: This is called PageHeader but also gets shown on the Send flow which is a full page

// this should be page header?

// then we will have full page header also?
interface PageHeaderProps {
  onClose?(): void;
  onGoBack?(): void;
  defaultClose?: boolean;
  defaultGoBack?: boolean;
  title?: string;
}

// this is supposed to be the same as the Home Header but with an 'X' to close after the menu

/** @deprecated */
export function PageHeader({
  onClose,
  onGoBack,
  title,
  defaultGoBack,
  defaultClose,
}: PageHeaderProps) {
  const navigate = useNavigate();

  function defaultCloseAction() {
    navigate(RouteUrls.Home);
  }
  function defaultGoBackAction() {
    navigate(-1);
  }

  const hasCloseIcon = onClose || defaultClose;
  return (
    <Flex
      alignItems="center"
      justifyContent="space-between"
      p="space.04"
      position="relative"
      // maxWidth="500px"
    >
      {onGoBack || defaultGoBack ? (
        <Box flexBasis="32.5%">
          <Button
            data-testid={SharedComponentsSelectors.PageHeaderBackBtn}
            alignSelf="center"
            onClick={onGoBack || defaultGoBackAction}
            variant="ghost"
          >
            <ArrowLeftIcon />
          </Button>
        </Box>
      ) : (
        <Box flexBasis="32.5%" />
      )}

      {title && (
        <Flex alignItems="center" flexBasis="35%" justifyContent="center">
          <styled.h5 textStyle="heading.05" color="colors.accent.background-secondary">
            {title}
          </styled.h5>
        </Flex>
      )}
      <Flex alignItems="center" flexBasis="32.5%" justifyContent="flex-end" position="relative">
        <NetworkModeBadge />
        {hasCloseIcon && (
          <Button ml="space.02" onClick={onClose || defaultCloseAction} variant="ghost">
            <CloseIcon />
          </Button>
        )}
      </Flex>
    </Flex>
  );
}
