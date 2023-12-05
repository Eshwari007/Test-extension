import { Route, useNavigate } from 'react-router-dom';

import { RouteUrls } from '@shared/route-urls';

import { useOnboardingState } from '@app/common/hooks/auth/use-onboarding-state';
import { useOnMount } from '@app/common/hooks/use-on-mount';
import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { ActivityList } from '@app/features/activity-list/activity-list';
import { AssetsList } from '@app/features/asset-list/asset-list';
import { FeedbackButton } from '@app/features/feedback-button/feedback-button';
import { InAppMessages } from '@app/features/hiro-messages/in-app-messages';
import { homePageModalRoutes } from '@app/routes/app-routes';
import { ModalBackgroundWrapper } from '@app/routes/components/modal-background-wrapper';
import { Header } from '@app/ui/components/containers/headers/header';

import { HomeLayout } from '../../ui/components/containers/home.layout';
import { CurrentAccount } from './components/account-area';
import { HomeTabs } from './components/home-tabs';

export function Home() {
  const { decodedAuthRequest } = useOnboardingState();

  const navigate = useNavigate();

  useRouteHeader(
    <>
      <InAppMessages />
      <Header variant="home" />
    </>
  );

  useOnMount(() => {
    if (decodedAuthRequest) navigate(RouteUrls.ChooseAccount);
  });

  return (
    <HomeLayout currentAccount={<CurrentAccount />}>
      <FeedbackButton />
      <HomeTabs>
        <ModalBackgroundWrapper>
          <Route index element={<AssetsList />} />
          <Route path={RouteUrls.Activity} element={<ActivityList />}>
            {homePageModalRoutes}
          </Route>

          {homePageModalRoutes}
        </ModalBackgroundWrapper>
      </HomeTabs>
    </HomeLayout>
  );
}
