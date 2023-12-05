import { Route } from 'react-router-dom';

import { RouteUrls } from '@shared/route-urls';

import { ThemesDialog } from '@app/features/dialogs/theme-dialog/theme-dialog';
import { SelectNetwork } from '@app/pages/select-network/select-network';
import { SignOutConfirmDialog } from '@app/pages/sign-out-confirm/sign-out-confirm';

export const settingsRoutes = (
  <Route>
    <Route path={RouteUrls.SignOutConfirm} element={<SignOutConfirmDialog />} />
    <Route path={RouteUrls.ChangeTheme} element={<ThemesDialog />} />
    <Route path={RouteUrls.SelectNetwork} element={<SelectNetwork />} />
  </Route>
);
