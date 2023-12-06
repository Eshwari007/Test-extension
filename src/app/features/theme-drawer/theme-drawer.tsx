import { useNavigate } from 'react-router-dom';

import { useLocationState } from '@app/common/hooks/use-location-state';
import { useBackgroundLocationRedirect } from '@app/routes/hooks/use-background-location-redirect';
import { BaseDrawer } from '@app/ui/components/containers/drawer/base-drawer';

import { ThemeList } from './theme-list';

export function ThemesDrawer() {
  useBackgroundLocationRedirect();
  const navigate = useNavigate();
  const backgroundLocation = useLocationState<Location>('backgroundLocation');
  return (
    <BaseDrawer title="Select Theme" isShowing onClose={() => navigate(backgroundLocation ?? '..')}>
      <ThemeList />
    </BaseDrawer>
  );
}
