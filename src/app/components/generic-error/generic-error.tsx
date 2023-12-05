import { ReactNode } from 'react';

import { FlexProps, styled } from 'leather-styles/jsx';

import { closeWindow } from '@shared/utils';

import { useRouteHeader } from '@app/common/hooks/use-route-header';
import { Header } from '@app/ui/components/containers/header';

import { GenericErrorLayout } from './generic-error.layout';

export function GenericErrorListItem({ text }: { text: ReactNode }) {
  return <styled.li mt="space.04">{text}</styled.li>;
}

interface GenericErrorProps extends FlexProps {
  body: string;
  helpTextList: ReactNode[];
  onClose?(): void;
  title: string;
}

export function GenericError(props: GenericErrorProps) {
  const { body, helpTextList, onClose = () => closeWindow(), title, ...rest } = props;

  useRouteHeader(<Header />);

  return (
    <GenericErrorLayout
      body={body}
      helpTextList={helpTextList}
      onClose={onClose}
      title={title}
      {...rest}
    />
  );
}
