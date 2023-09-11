import { useNavigate } from 'react-router-dom';

import { Box } from 'leather-styles/jsx';

import { RouteUrls } from '@shared/route-urls';

import { GenericError } from '@app/components/generic-error/generic-error';

const body = 'Check balance and try again';
const helpTextList = [
  <Box as="li" mt="space.04" key={1}>
    <styled.span>Possibly caused by api issues</styled.span>
  </Box>,
];
const title = 'Unable to calculate fees';

export function FeesListError() {
  const navigate = useNavigate();

  return (
    <Box textAlign="center" px={['unset', 'loose']} py="space.04" width="100%">
      <GenericError
        body={body}
        helpTextList={helpTextList}
        onClose={() => navigate(RouteUrls.SendCryptoAsset)}
        title={title}
      />
    </Box>
  );
}
