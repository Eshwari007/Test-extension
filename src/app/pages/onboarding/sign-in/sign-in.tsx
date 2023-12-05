import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { RouteUrls } from '@shared/route-urls';

import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { createNullArrayOfLength } from '@app/common/utils';
import { MnemonicForm } from '@app/pages/onboarding/sign-in/mnemonic-form';
import { HomeHeader } from '@app/ui/components/containers/headers/home-header';
import { TwoColumnLayout } from '@app/ui/components/containers/two-column.layout';

import { SignInContent } from './components/sign-in.content';

export function SignIn() {
  const navigate = useNavigate();

  const [twentyFourWordMode, setTwentyFourWordMode] = useState(true);
  const [mnemonic, setMnemonic] = useState<(string | null)[]>([]);

  useRouteHeader(<HomeHeader onClose={() => navigate(RouteUrls.Onboarding)} />);

  useEffect(() => {
    const emptyMnemonicArray = twentyFourWordMode
      ? createNullArrayOfLength(24)
      : createNullArrayOfLength(12);
    setMnemonic(emptyMnemonicArray);
  }, [twentyFourWordMode]);

  return (
    <>
      <TwoColumnLayout
        leftColumn={
          <SignInContent
            onClick={() => setTwentyFourWordMode(!twentyFourWordMode)}
            twentyFourWordMode={twentyFourWordMode}
          />
        }
        rightColumn={
          <MnemonicForm
            mnemonic={mnemonic}
            setMnemonic={setMnemonic}
            twentyFourWordMode={twentyFourWordMode}
          />
        }
      />
    </>
  );
}
