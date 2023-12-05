import type { Meta } from '@storybook/react';

import { Header as Component, HeaderProps } from './header';

const meta: Meta<typeof Component> = {
  component: Component,
  tags: ['autodocs'],
  title: 'Design System/Containers/Header',
  args: {
    variant: 'home',
  },
};

export default meta;

export function Header(args: HeaderProps) {
  return <Component {...args} onClose={() => null} onGoBack={() => null} />;
}

export function BigTitleHeader() {
  return <Component variant="big-title" title="Choose asset to receive" onClose={() => null} />;
}

export function PageHeader(args: HeaderProps) {
  return <Component {...args} title="Some page" onGoBack={() => null} />;
}
