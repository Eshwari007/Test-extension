import { Flex, styled } from 'leather-styles/jsx';

// TODO - need to refactor this so network is checked at top level and can be passed to page container
export function NetworkModeBadge({
  isTestnetChain,
  name,
  onClick,
}: {
  isTestnetChain: boolean;
  name: string;
  onClick(): void;
}) {
  if (!isTestnetChain) return null;

  return (
    <Flex
      _hover={{ cursor: 'pointer' }}
      alignItems="center"
      border="subdued"
      borderRadius="md"
      height="24px"
      onClick={onClick}
      px="space.03"
      position="relative"
      zIndex={999}
    >
      <styled.span color="accent.text-subdued" textStyle="label.03">
        {name}
      </styled.span>
    </Flex>
  );
}
