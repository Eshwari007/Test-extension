import { useCallback, useRef } from 'react';

import { useEventListener } from '@app/common/hooks/use-event-listener';
import { useOnClickOutside } from '@app/common/hooks/use-onclickoutside';

export function useDrawer(isShowing: boolean, onClose: () => void, pause?: boolean) {
  const ref = useRef(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isShowing && e.key === 'Escape') {
        onClose();
      }
    },
    [onClose, isShowing]
  );

  useOnClickOutside(ref, !pause && isShowing ? onClose : null);
  useEventListener('keydown', handleKeyDown);

  return ref;
}
