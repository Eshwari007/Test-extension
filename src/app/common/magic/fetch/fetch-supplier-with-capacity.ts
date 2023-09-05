import { hexToBytes } from '@stacks/common';

import { pubKeyToBtcAddress } from '../utils';
import type { MagicFetchContextWithElectrum } from './constants';
import { fetchBitcoinAddressBalanceForPublicKey } from './fetch-bitcoin-address-balance-for-public-key';
import { fetchSupplier } from './fetch-supplier';

/**
 * Fetches a supplier with balance, fees, and capacity from the Magic contracts.
 *
 * @param id      The supplier ID.
 * @param context The context.
 */
export async function fetchSupplierWithCapacity(
  id: number,
  context: MagicFetchContextWithElectrum
) {
  const supplier = await fetchSupplier(id, context);

  const publicKey = hexToBytes(supplier.publicKey);
  const address = pubKeyToBtcAddress(publicKey, context.network);

  const btc = await fetchBitcoinAddressBalanceForPublicKey(publicKey, context);

  return {
    ...supplier,
    btcAddress: address,
    btc: btc.toString(),
  };
}
