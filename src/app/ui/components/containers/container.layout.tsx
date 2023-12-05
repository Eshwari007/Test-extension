import { radixBaseCSS } from '@radix-ui/themes/styles.css';
import { css } from 'leather-styles/css';
import { Flex } from 'leather-styles/jsx';

interface ContainerLayoutProps {
  children: React.JSX.Element | React.JSX.Element[];
  header: React.JSX.Element | null;
}
export function ContainerLayout({ children, header }: ContainerLayoutProps) {
  return (
    <Flex
      flexDirection="column"
      flexGrow={1}
      width="100%"
      height="100%"
      className={css(radixBaseCSS)}
    >
      {header || null}
      <Flex className="main-content" flexGrow={1} position="relative" width="100%">
        {children}
      </Flex>
    </Flex>
  );
}
