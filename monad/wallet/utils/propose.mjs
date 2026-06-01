import { createPublicClient, http, encodeFunctionData, hashTypedData, getAddress } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import qrcode from 'qrcode-terminal';

// ----- Generic Safe transaction proposer -----
//
// Required env vars:
//   CHAIN_ID       — 143 (mainnet) or 10143 (testnet)
//   SAFE_ADDRESS   — checksummed Safe multisig address
//   PRIVATE_KEY    — agent wallet private key
//
// Transaction mode (pick ONE):
//
//   A) Contract deployment (delegatecall into CreateCall):
//      DEPLOYMENT_BYTECODE — raw creation bytecode
//
//   B) Arbitrary transaction (direct call to any contract):
//      TX_TO    — target contract address
//      TX_DATA  — encoded calldata (hex)
//      TX_VALUE — value in wei (optional, defaults to "0")

const NETWORKS = {
  143:   { rpcUrl: 'https://rpc.monad.xyz',         txService: 'https://api.safe.global/tx-service/monad/api/v1',         safePrefix: 'monad' },
  10143: { rpcUrl: 'https://testnet-rpc.monad.xyz',  txService: 'https://api.safe.global/tx-service/monad-testnet/api/v1', safePrefix: 'monad-testnet' },
};

const CREATE_CALL_ADDRESS = '0x9b35Af71d77eaf8d7e40252370304687390A1A52';

const CHAIN_ID = Number(process.env.CHAIN_ID);
const network = NETWORKS[CHAIN_ID];
if (!network) {
  console.error(`❌ Unsupported CHAIN_ID: ${CHAIN_ID}. Use 143 (mainnet) or 10143 (testnet).`);
  process.exit(1);
}

const SAFE_ADDRESS = getAddress(process.env.SAFE_ADDRESS);

function buildTransaction() {
  // Mode A: contract deployment via CreateCall
  if (process.env.DEPLOYMENT_BYTECODE) {
    const createCallData = encodeFunctionData({
      abi: [{
        name: 'performCreate',
        type: 'function',
        inputs: [{ name: 'value', type: 'uint256' }, { name: 'deploymentData', type: 'bytes' }],
        outputs: [{ name: '', type: 'address' }],
      }],
      functionName: 'performCreate',
      args: [0n, process.env.DEPLOYMENT_BYTECODE],
    });
    return { to: CREATE_CALL_ADDRESS, value: '0', data: createCallData, operation: 1 }; // DELEGATECALL
  }

  // Mode B: arbitrary contract call
  if (process.env.TX_TO && process.env.TX_DATA) {
    return {
      to: getAddress(process.env.TX_TO),
      value: process.env.TX_VALUE || '0',
      data: process.env.TX_DATA,
      operation: 0, // CALL
    };
  }

  console.error('❌ Provide either DEPLOYMENT_BYTECODE (deploy) or TX_TO + TX_DATA (contract call).');
  process.exit(1);
}

async function main() {
  const account = privateKeyToAccount(process.env.PRIVATE_KEY);
  console.log(`✅ Agent address: ${account.address}`);
  console.log(`✅ Network: ${network.safePrefix} (chain ${CHAIN_ID})`);

  const publicClient = createPublicClient({
    transport: http(network.rpcUrl),
  });

  const nonce = await publicClient.readContract({
    address: SAFE_ADDRESS,
    abi: [{ name: 'nonce', type: 'function', stateMutability: 'view', inputs: [], outputs: [{ type: 'uint256' }] }],
    functionName: 'nonce',
  });

  console.log(`✅ Safe nonce: ${nonce}`);

  const { to, value, data, operation } = buildTransaction();

  const txData = {
    to,
    value,
    data,
    operation,
    safeTxGas: '0',
    baseGas: '0',
    gasPrice: '0',
    gasToken: '0x0000000000000000000000000000000000000000',
    refundReceiver: '0x0000000000000000000000000000000000000000',
    nonce: nonce.toString(),
  };

  const domain = {
    chainId: CHAIN_ID,
    verifyingContract: SAFE_ADDRESS,
  };

  const types = {
    SafeTx: [
      { name: 'to', type: 'address' },
      { name: 'value', type: 'uint256' },
      { name: 'data', type: 'bytes' },
      { name: 'operation', type: 'uint8' },
      { name: 'safeTxGas', type: 'uint256' },
      { name: 'baseGas', type: 'uint256' },
      { name: 'gasPrice', type: 'uint256' },
      { name: 'gasToken', type: 'address' },
      { name: 'refundReceiver', type: 'address' },
      { name: 'nonce', type: 'uint256' },
    ],
  };

  // Sign with EIP-712
  console.log('✍️  Signing with EIP-712...');
  const signature = await account.signTypedData({
    domain,
    types,
    primaryType: 'SafeTx',
    message: txData,
  });

  const txHash = hashTypedData({
    domain,
    types,
    primaryType: 'SafeTx',
    message: txData,
  });

  console.log(`✅ Transaction hash: ${txHash}`);
  console.log(`✅ Agent signed (1/2)`);

  // POST to Transaction Service API
  console.log('📤 Posting to Transaction Service API...');
  const response = await fetch(`${network.txService}/safes/${SAFE_ADDRESS}/multisig-transactions/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...txData,
      contractTransactionHash: txHash,
      sender: account.address,
      signature,
    }),
  });

  if (response.ok) {
    const safeUrl = `https://app.safe.global/transactions/queue?safe=${network.safePrefix}:${SAFE_ADDRESS}`;
    console.log('✅ Transaction proposed successfully!');
    console.log('');
    console.log('🎉 Transaction appears in Safe UI queue!');
    console.log('');
    console.log('Scan QR code to approve on mobile:');
    console.log('');
    qrcode.generate(safeUrl, { small: true });
    console.log('');
    console.log('User can now:');
    console.log(`1. Open: ${safeUrl}`);
    console.log('2. See pending transaction (Agent already signed 1/2)');
    console.log('3. Sign with their wallet (2/2)');
    console.log('4. Execute');
  } else {
    const error = await response.text();
    console.error(`❌ API Error: ${response.status}`);
    console.error(error);
    process.exit(1);
  }
}

main();