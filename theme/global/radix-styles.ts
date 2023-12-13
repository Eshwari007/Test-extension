export const radixStyles = {
  '.radix-themes': {
    '--font-size-7': '32px',
    '--font-size-8': '44px',
    '--font-size-9': '53px',

    '--default-font-family': '"Diatype", "Helvetica Neue", sans-serif',
    '--heading-font-family': '"Marche", "Helvetica Neue", sans-serif',

    '--letter-spacing-1': 0,
    '--letter-spacing-2': 0,
    '--letter-spacing-3': 0,
    '--letter-spacing-4': 0,
    '--letter-spacing-5': 0,
    '--letter-spacing-6': 0,
    '--letter-spacing-7': 0,
    '--letter-spacing-8': 0,
    '--letter-spacing-9': 0,

    // Configured to Diatype
    '--font-weight-light': 400,
    '--font-weight-regular': 400,
    '--font-weight-medium': 500,
    '--font-weight-bold': 500,

    '--color-overlay': 'rgba(0, 0, 0, 0.3)', //check this
  },

  // TODO check if these are being set properly
  ':root, .light, .light-theme': {
    '--brown-1': 'brown.1',
    '--brown-2': 'brown.2',
    '--brown-3': 'brown.3',
    '--brown-4': 'brown.4',
    '--brown-5': 'brown.5',
    '--brown-6': 'brown.6',
    '--brown-7': 'brown.7',
    '--brown-8': 'brown.8',
    '--brown-9': 'brown.9',
    '--brown-10': 'brown.10',
    '--brown-11': 'brown.11',
    '--brown-12': 'brown.12',

    '--gray-1': 'ink.1',
    '--gray-2': 'ink.2',
    '--gray-3': 'ink.3',
    '--gray-4': 'ink.4',
    '--gray-5': 'ink.5',
    '--gray-6': 'ink.6',
    '--gray-7': 'ink.7',
    '--gray-8': 'ink.8',
    '--gray-9': 'ink.9',
    '--gray-10': 'ink.10',
    '--gray-11': 'ink.11',
    '--gray-12': 'ink.12',
  },
  '.dark, .dark-theme': {
    '--brown-1': 'brown.1',
    '--brown-2': 'brown.2',
    '--brown-3': 'brown.3',
    '--brown-4': 'brown.4',
    '--brown-5': 'brown.5',
    '--brown-6': 'brown.6',
    '--brown-7': 'brown.7',
    '--brown-8': 'brown.8',
    '--brown-9': 'brown.9',
    '--brown-10': 'brown.10',
    '--brown-11': 'brown.11',
    '--brown-12': 'brown.12',

    '--gray-1': 'ink.1',
    '--gray-2': 'ink.2',
    '--gray-3': 'ink.3',
    '--gray-4': 'ink.4',
    '--gray-5': 'ink.5',
    '--gray-6': 'ink.6',
    '--gray-7': 'ink.7',
    '--gray-8': 'ink.8',
    '--gray-9': 'ink.9',
    '--gray-10': 'ink.10',
    '--gray-11': 'ink.11',
    '--gray-12': 'ink.12',
  },
};

// override the radix tabs color
export const radixTabStyles = {
  '.rt-TabsList.rt-r-size-2': {
    height: 'auto',
    '--tabs-trigger-inner-padding-y': 'spacing.space.04',
  },
  '.rt-TabsTrigger': {
    flex: 1,
    '& :hover::before': {
      backgroundColor: 'accent.component-background-hover',
    },
  },
  '.rt-TabsTriggerInner': {
    width: '100%',
  },
  '.rt-TabsTrigger[data-state="active"]::before': {
    backgroundColor: 'accent.text-primary',
  },
  // #4250 TODO this removes bottom padding of Dialog.Root.
  // if used refactor to move into it's own style obj
  '.rt-DialogOverlay': {
    paddingBottom: 0,
  },
  // '.DialogOverlay' : {
  //   background-color: var(--black-a9);
  //   position: fixed;
  //   inset: 0;
  //   animation: overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1);
  // }
};

// const radixDialog = {

// .DialogOverlay {
//   background-color: var(--black-a9);
//   position: fixed;
//   inset: 0;
//   animation: overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1);
// // }

// .DialogContent {
// background-color: white;
// border-radius: 6px;
// box-shadow: hsl(206 22% 7% / 35%) 0px 10px 38px -10px, hsl(206 22% 7% / 20%) 0px 10px 20px -15px;
// position: fixed;
// top: 50%;
// left: 50%;
// transform: translate(-50%, -50%);
// width: 90vw;
// max-width: 450px;
// max-height: 85vh;
// padding: 25px;
// animation: contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1);
// }
// .DialogContent:focus {
//   outline: none;
// }

// .DialogTitle {
//   margin: 0;
//   font-weight: 500;
//   color: var(--mauve-12);
//   font-size: 17px;
// }

// .DialogDescription {
//   margin: 10px 0 20px;
//   color: var(--mauve-11);
//   font-size: 15px;
//   line-height: 1.5;
// }

// @keyframes overlayShow {
//   from {
//     opacity: 0;
//   }
//   to {
//     opacity: 1;
//   }
// }

// @keyframes contentShow {
//   from {
//     opacity: 0;
//     transform: translate(-50%, -48%) scale(0.96);
//   }
//   to {
//     opacity: 1;
//     transform: translate(-50%, -50%) scale(1);
//   }
// }
// }
