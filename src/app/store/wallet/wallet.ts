import { atom } from 'jotai';
import { fetchWalletConfig, createWalletGaiaConfig } from '@stacks/wallet-sdk';
import { gaiaUrl } from '@shared/constants';
import { textToBytes } from '@app/common/store-utils';
import { storeAtom } from '..';
import { deriveWalletWithAccounts } from '../chains/stx-chain.selectors';

export const walletState = atom(async get => {
  const store = get(storeAtom);
  if (!store.keys.entities.default) return;
  if (!store.inMemoryKeys.keys.default) return;
  return deriveWalletWithAccounts(
    store.inMemoryKeys.keys.default,
    store.chains.stx.default.highestAccountIndex
  );
});

export const walletConfigState = atom(async get => {
  const wallet = get(walletState);
  if (!wallet) return null;
  const gaiaHubConfig = await createWalletGaiaConfig({ wallet, gaiaHubUrl: gaiaUrl });
  return fetchWalletConfig({ wallet, gaiaHubConfig });
});

export const encryptedSecretKeyState = atom(get => {
  const store = get(storeAtom);
  return store.keys.entities.default?.encryptedSecretKey;
});

export const currentAccountIndexState = atom(get => {
  const store = get(storeAtom);
  return store.chains.stx.default.currentAccountIndex;
});

export const secretKeyState = atom(get => {
  const store = get(storeAtom);
  return store.inMemoryKeys.keys.default ? textToBytes(store.inMemoryKeys.keys.default) : undefined;
});