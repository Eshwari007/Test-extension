import { useNavigate } from 'react-router-dom';

import { styled } from 'leather-styles/jsx';

import { ExternalLink } from '@app/components/external-link';
import { UnsupportedBrowserImg } from '@app/features/ledger/illustrations/ledger-illu-unsupported-browser';
import { BaseDrawer } from '@app/ui/components/containers/drawer/base-drawer';

import { LedgerTitle } from '../../components/ledger-title';
import { LedgerWrapper } from '../../components/ledger-wrapper';

export function UnsupportedBrowserLayout() {
  const navigate = useNavigate();

  return (
    <BaseDrawer isShowing onClose={() => navigate(-1)}>
      <LedgerWrapper image={<UnsupportedBrowserImg />}>
        <LedgerTitle mb="space.03">Your browser isn't supported</LedgerTitle>
        <styled.span textStyle="label.03" color="accent.text-subdued">
          {'To connect your Ledger with Leather try '}
          <ExternalLink textDecoration="underline" href="https://www.google.com/chrome/">
            Chrome
          </ExternalLink>
          {' or '}
          <ExternalLink textDecoration="underline" href="https://brave.com/download/">
            Brave
          </ExternalLink>
          .
        </styled.span>
      </LedgerWrapper>
    </BaseDrawer>
  );
}
