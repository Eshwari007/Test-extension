import React from 'react';

import { HomePageSelectors } from '@tests/selectors/home.selectors';
import { Stack } from 'leather-styles/jsx';

import { AccountInfoCard } from '../../../pages/home/components/account-info-card';

//  FIXME 4370 - move this const somewhere else, maybe with POPOUT size in src/shared/constants? with the other viewports? Use a breakpoint token?
export const HOME_MAX_WIDTH = '882px';

type HomeLayoutProps = Record<'currentAccount' | 'children', React.ReactNode>;
export function HomeLayout({ children }: HomeLayoutProps) {
  return (
    <Stack alignItems="center" width="100%" mx={['', 'space.04']}>
      <Stack
        data-testid={HomePageSelectors.HomePageContainer}
        maxWidth={['unset', 'unset', HOME_MAX_WIDTH]}
        px={['space.04', 'space.04', 'space.08']}
        width="100%"
        backgroundColor="ink.1"
        borderRadius="lg"
      >
        <AccountInfoCard />
        {children}
      </Stack>
    </Stack>
  );
}
