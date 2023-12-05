import { Stack, StackProps } from 'leather-styles/jsx';

export function SwapAssetListLayout({ children }: StackProps) {
  return (
    // TODO check 4370
    // maxHeight added to prevent overflow of content
    // - improve this to use virtuoso? / the style of maxHeight
    <Stack gap="space.06" pb="space.05" width="100%" maxHeight={{ base: '80vh', md: '50vh' }}>
      {children}
    </Stack>
  );
}
