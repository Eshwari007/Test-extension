import { useNavigate } from 'react-router-dom';

import { useLocationState } from '@app/common/hooks/use-location-state';
import { useBackgroundLocationRedirect } from '@app/routes/hooks/use-background-location-redirect';
import { Dialog } from '@app/ui/components/containers/dialog/dialog';

import { ThemeList } from './theme-list';

export function ThemesDialog() {
  useBackgroundLocationRedirect();
  const navigate = useNavigate();
  const backgroundLocation = useLocationState<Location>('backgroundLocation');
  return (
    <Dialog title="Select Theme" isShowing onClose={() => navigate(backgroundLocation ?? '..')}>
      <ThemeList />
    </Dialog>
  );
}
