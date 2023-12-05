import { ReactNode } from 'react';

import { Box, Flex, styled } from 'leather-styles/jsx';

import { isString } from '@shared/utils';

import { ArrowLeftIcon } from '@app/ui/components/icons/arrow-left-icon';
import { CloseIcon } from '@app/ui/components/icons/close-icon';

import { HeaderActionButton } from './header-action-button';

// 4370 TODO assess this
// - can we replace it with <Header
// - make sure X always shows on right
interface DialogHeaderProps {
  enableGoBack?: boolean;
  isWaitingOnPerformedAction?: boolean;
  onClose?(): void;
  onGoBack(): void;
  title?: ReactNode;
  waitingOnPerformedActionMessage?: string;
}

/** @deprecated */
export function DialogHeader({
  enableGoBack,
  isWaitingOnPerformedAction,
  onClose,
  onGoBack,
  title,
  waitingOnPerformedActionMessage,
}: DialogHeaderProps) {
  return (
    <Flex justifyContent="space-between" alignItems="center" p="space.04">
      {enableGoBack ? (
        <HeaderActionButton
          icon={<ArrowLeftIcon />}
          isWaitingOnPerformedAction={isWaitingOnPerformedAction}
          onAction={onGoBack}
        />
      ) : isString(title) ? (
        <Box width="36px" height="36px" />
      ) : null}

      {title && isString(title) ? <styled.h1 textStyle="heading.05">{title}</styled.h1> : title}
      {isWaitingOnPerformedAction && (
        <styled.span color="accent.text-subdued" textStyle="caption.01">
          {waitingOnPerformedActionMessage}
        </styled.span>
      )}
      {onClose && (
        <HeaderActionButton
          icon={<CloseIcon />}
          isWaitingOnPerformedAction={isWaitingOnPerformedAction}
          onAction={onClose}
        />
      )}
    </Flex>
  );
}
