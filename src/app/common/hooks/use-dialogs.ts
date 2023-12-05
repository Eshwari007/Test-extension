import {
  useShowHighFeeConfirmationState,
  useShowSettingsStore,
  useShowSwitchAccountsState,
  useShowTxSettingsCallback,
} from '@app/store/ui/ui.hooks';

//  TODO move this to features/dialogs?
export function useDialogs() {
  const [isShowingAccounts, setIsShowingSwitchAccountsState] = useShowSwitchAccountsState();
  const [isShowingHighFeeConfirmation, setIsShowingHighFeeConfirmation] =
    useShowHighFeeConfirmationState();

  const [isShowingSettings, setIsShowingSettings] = useShowSettingsStore();
  const [isShowingTxSettingsCallback, setIsShowingTxSettingsCallback] = useShowTxSettingsCallback();

  return {
    isShowingAccounts,
    setIsShowingSwitchAccountsState,
    isShowingHighFeeConfirmation,
    setIsShowingHighFeeConfirmation,
    isShowingSettings,
    setIsShowingSettings,
    isShowingTxSettingsCallback,
    setIsShowingTxSettingsCallback,
  };
}
