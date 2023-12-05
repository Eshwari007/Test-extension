import { styled } from 'leather-styles/jsx';

import { LeatherIcon } from '@app/ui/components/icons/leather-icon';

interface LeatherLogoProps {
  onClick?(): void;
}
export function LeatherLogo({ onClick, ...rest }: LeatherLogoProps) {
  return (
    <styled.button
      _hover={onClick && { color: 'accent.action-primary-hover' }}
      color="accent.text-primary"
      cursor={onClick ? 'pointer' : 'unset'}
      height="32px"
      onClick={onClick ? onClick : undefined}
      width="76px"
      {...rest}
    >
      <LeatherIcon />
    </styled.button>
  );
}
