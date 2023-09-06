import { FiFastForward } from 'react-icons/fi';

import { Box, Button } from 'leather-styles/jsx';

interface IncreaseFeeButtonProps {
  isEnabled?: boolean;
  isHovered: boolean;
  isSelected: boolean;
  onIncreaseFee(): void;
}
export function IncreaseFeeButton(props: IncreaseFeeButtonProps) {
  const { isEnabled, isHovered, isSelected, onIncreaseFee } = props;
  const isActive = isEnabled && isHovered && !isSelected;

  return (
    <Button
      _hover={{
        color: token('colors.accent.action-primary-default'),
      }}
      color={color('text-body')}
      fontSize={0}
      minWidth="105px"
      ml="auto"
      mode="tertiary"
      onClick={e => {
        onIncreaseFee();
        e.stopPropagation();
      }}
      opacity={!isActive ? 0 : 1}
      pointerEvents={!isActive ? 'none' : 'all'}
      size="sm"
      zIndex={999}
    >
      <Box mr="3px" as={FiFastForward} color={color('accent')} />
      Increase fee
    </Button>
  );
}
