import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

import { useRouteHeaderState } from '@app/store/ui/ui.hooks';

// Seems this is used to not show any header on some pages, for example on `Swap` or `Send`
export function useRouteHeader(header: React.JSX.Element, isParentRoute?: boolean) {
  const location = useLocation();
  const [_, setRouteHeader] = useRouteHeaderState();
  useEffect(() => {
    if (location.state?.hasHeaderTitle && isParentRoute) {
      return;
    }
    setRouteHeader(header);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);
}
