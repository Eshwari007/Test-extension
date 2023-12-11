import { useNavigate } from 'react-router-dom';

import { SharedComponentsSelectors } from '@tests/selectors/shared-component.selectors';
import { Box, Flex, styled } from 'leather-styles/jsx';

import { RouteUrls } from '@shared/route-urls';

import { NetworkModeBadge } from '@app/components/network-mode-badge';
import { LeatherButton } from '@app/ui/components/button';
import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { CloseIcon } from '@app/ui/components/icons/close-icon';

// This is called ModalHeader but also gets shown on the Send flow which is a full page

interface ModalHeaderProps {
  onClose?(): void;
  onGoBack?(): void;
  defaultClose?: boolean;
  defaultGoBack?: boolean;
  title?: string;
}

export function ModalHeader({
  onClose,
  onGoBack,
  title,
  defaultGoBack,
  defaultClose,
}: ModalHeaderProps) {
  const navigate = useNavigate();

  function defaultCloseAction() {
    navigate(RouteUrls.Home);
  }
  function defaultGoBackAction() {
    navigate(-1);
  }

  const hasCloseIcon = onClose || defaultClose;
  return (
    <Flex alignItems="center" justifyContent="space-between" p="space.04" position="relative">
      {onGoBack || defaultGoBack ? (
        <Box flexBasis="32.5%">
          <LeatherButton
            data-testid={SharedComponentsSelectors.ModalHeaderBackBtn}
            alignSelf="center"
            onClick={onGoBack || defaultGoBackAction}
            variant="ghost"
          >
            <ArrowLeftIcon />
          </LeatherButton>
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
        {!hasCloseIcon && (
          <LeatherButton ml="space.02" onClick={onClose || defaultCloseAction} variant="ghost">
            <CloseIcon />
          </LeatherButton>
        )}
      </Flex>
    </Flex>
  );
}
