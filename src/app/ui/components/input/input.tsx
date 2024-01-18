import {
  type ComponentProps,
  LegacyRef,
  createContext,
  forwardRef,
  useContext,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';

import { sva } from 'leather-styles/css';
import { SystemStyleObject } from 'leather-styles/types';

import { useOnMount } from '@app/common/hooks/use-on-mount';
import { propIfDefined } from '@app/common/utils';
import { createStyleContext } from '@app/ui/utils/style-context';

const hackyDelayOneMs = 1;

const transformedLabelStyles: SystemStyleObject = {
  textStyle: 'label.03',
  transform: 'translateY(-12px)',
  fontWeight: 500,
};

const input = sva({
  slots: ['root', 'label', 'input'],
  base: {
    root: {
      display: 'block',
      pos: 'relative',
      minHeight: '64px',
      p: 'space.04',
      ring: 'none',
      textStyle: 'body.02',
      zIndex: 4,
      color: 'accent.text-subdued',
      _before: {
        content: '""',
        rounded: 'xs',
        pos: 'absolute',
        top: '-1px',
        left: '-1px',
        right: '-1px',
        bottom: '-1px',
        border: '3px solid transparent',
        zIndex: 9,
        pointerEvents: 'none',
      },
      _focusWithin: {
        '& label': { color: 'accent.text-primary', ...transformedLabelStyles },
        _before: {
          border: 'action',
          borderWidth: '2px',
        },
      },
      '&[data-has-error="true"]': {
        color: 'error.label',
        _before: {
          borderColor: 'error.label',
          borderWidth: '2px',
        },
      },
    },
    input: {
      background: 'transparent',
      appearance: 'none',
      rounded: 'xs',
      pos: 'absolute',
      px: 'space.04',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 5,
      textStyle: 'body.01',
      color: 'accent.text-primary',
      border: '1px solid',
      borderColor: 'accent.border-hover',
      _disabled: {
        bg: 'accent.component-background-default',
        borderColor: 'accent.non-interactive',
        cursor: 'not-allowed',
      },
      _focus: { ring: 'none' },
      _placeholder: { color: 'accent.text-subdued' },
      '&:placeholder-shown + label': transformedLabelStyles,
      '[data-has-label="true"] &': {
        pt: '22px',
        pb: '4px',
      },
    },
    label: {
      pointerEvents: 'none',
      pos: 'absolute',
      top: '36%',
      left: 'space.04',
      zIndex: 9,
      color: 'inherit',
      textStyle: 'body.02',
      transition: 'font-size 100ms ease-in-out, transform 100ms ease-in-out',
      // Move the input's label to the top when the input has a value
      '[data-has-value="true"] &': transformedLabelStyles,
      '[data-shrink="true"] &': transformedLabelStyles,
    },
  },
});

type InputChldren = 'root' | 'label' | 'input';

const { withProvider, withContext } = createStyleContext(input);

interface InputContextProps {
  hasValue: boolean;
  setHasValue(hasValue: boolean): void;
  registerChild(child: string): void;
  children: InputChldren[];
}

const InputContext = createContext<InputContextProps | null>(null);

function useInputContext() {
  const context = useContext(InputContext);
  if (!context) throw new Error('useInputContext must be used within an Input.Root');
  return context;
}

const RootBase = withProvider('div', 'root');

interface RootProps extends ComponentProps<'div'> {
  hasError?: boolean;
  /**
   * Display the label in a top fixed position. Often necessary when
   * programmatically updating inputs, similar to issues described here
   * https://mui.com/material-ui/react-text-field/#limitations
   */
  shrink?: boolean;
}
function Root({ hasError, shrink, ...props }: RootProps) {
  const [hasValue, setHasValue] = useState(false);
  const [children, setChildren] = useState<InputChldren[]>(['root']);

  function registerChild(child: InputChldren) {
    setChildren(children => [...children, child]);
  }

  const dataAttrs = {
    ...propIfDefined('data-has-error', hasError),
    ...propIfDefined('data-shrink', shrink),
    'data-has-label': children.includes('label'),
  };

  return (
    <InputContext.Provider value={{ hasValue, setHasValue, children, registerChild }}>
      <RootBase data-has-value={hasValue} {...dataAttrs} {...props} />
    </InputContext.Provider>
  );
}

const FieldBase = withContext('input', 'input');

const Field = forwardRef((props: ComponentProps<'input'>, ref) => {
  const { setHasValue } = useInputContext();
  const innerRef = useRef<HTMLInputElement | null>(null);

  useImperativeHandle(ref, () => innerRef.current);

  // We need to determine whether the input has a value on it's initial
  // render. In many places we use Formik to apply default form values.
  // Formik sets these values after the initial render, so we need to wait
  // before doing this check to see if there's a value.
  useOnMount(
    () =>
      void setTimeout(() => {
        if (innerRef.current?.value !== '') setHasValue(true);
      }, hackyDelayOneMs)
  );

  return (
    <FieldBase
      ref={innerRef}
      {...props}
      onInput={e => {
        // Note: this logic to determine if the field is empty may have to be
        // made dynamic to `input=type`, and potentially made configurable with
        // a callback passed to `Input.Root` e.g.
        // ```
        //    <Input.Root isEmptyFn={value => typeof value === 'number' && value <= 0} />
        // ```
        if (e.target instanceof HTMLInputElement) setHasValue(e.target.value !== '');
        props.onInput?.(e);
      }}
    />
  );
});

const LabelBase = withContext('label', 'label');

const Label = forwardRef((props: ComponentProps<'label'>, ref: LegacyRef<HTMLLabelElement>) => {
  const { registerChild } = useInputContext();
  useOnMount(() => registerChild('label'));
  return <LabelBase ref={ref} {...props} />;
});

export const Input = { Root, Field, Label };
