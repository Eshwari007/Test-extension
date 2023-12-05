import { memo } from 'react';

import { LeatherButton } from '@app/ui/components/button';
import { LeatherIcon } from '@app/ui/components/icons/leather-icon';

export const LeatherLogo = memo(({ onClick }: { onClick?: () => void }) => {
  return (
    <LeatherButton
      _hover={onClick && { color: 'accent.action-primary-hover' }}
      color="accent.text-primary"
      cursor={onClick ? 'pointer' : 'unset'}
      height="16px"
      onClick={onClick ? onClick : undefined}
      variant="text"
      width="76px"
    >
      <LeatherIcon />
    </LeatherButton>
  );
});
