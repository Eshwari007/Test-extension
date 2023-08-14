import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { RouteUrls } from '@shared/route-urls';

import { useTrackFirstDeposit } from '@app/common/hooks/analytics/transactions-analytics.hooks';
import { useOnboardingState } from '@app/common/hooks/auth/use-onboarding-state';
import { useLocationState } from '@app/common/hooks/use-location-state';
import { useOnMount } from '@app/common/hooks/use-on-mount';
import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { Header } from '@app/components/header';
import { ActivityList } from '@app/features/activity-list/activity-list';
import { AssetsList } from '@app/features/asset-list/asset-list';
import { InAppMessages } from '@app/features/hiro-messages/in-app-messages';
import { SuggestedFirstSteps } from '@app/features/suggested-first-steps/suggested-first-steps';
import { HomeActions } from '@app/pages/home/components/home-actions';
import { receiveRoutes, settingsModalRoutes } from '@app/routes/app-routes';

import { CurrentAccount } from './components/account-area';
import { HomeTabs } from './components/home-tabs';
import { HomeLayout } from './components/home.layout';

export function Home() {
  const { decodedAuthRequest } = useOnboardingState();

  const navigate = useNavigate();

  const location = useLocation();

  const backgroundLocation = useLocationState<Location>('backgroundLocation');
  useTrackFirstDeposit();

  useRouteHeader(
    <>
      <InAppMessages />
      <Header />
    </>
  );

  useOnMount(() => {
    if (decodedAuthRequest) navigate(RouteUrls.ChooseAccount);
  });
  return (
    <HomeLayout
      suggestedFirstSteps={<SuggestedFirstSteps />}
      currentAccount={<CurrentAccount />}
      actions={<HomeActions />}
    >
      <HomeTabs>
        <>
          <Routes location={backgroundLocation || location}>
            <Route index element={<AssetsList />} />
            <Route path={RouteUrls.Activity} element={<ActivityList />} />
            {/* Routes also need to be declared to work when opened in new tab */}
            {/* TODO- refactor this again so it's just one import */}
            {receiveRoutes}
            {settingsModalRoutes}
            <Route path="*" element={<Navigate replace to={RouteUrls.Home} />} />
          </Routes>
          {backgroundLocation && <Outlet />}
        </>
      </HomeTabs>
    </HomeLayout>
  );
}
