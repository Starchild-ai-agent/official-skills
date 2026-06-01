---
name: wallet
description: Send transactions on Monad testnet or mainnet using Agent wallet, the transactions could be for smart contract deployment, onchain actions like swapping or smart contract calls and signing messages
---

## ⚠️ CRITICAL: Safe Multisig Required - No Exceptions

Any transaction other than deploying a Safe multisig must be proposed to the user via the deployed multisig.

For instructions on how to create and use a Safe multisig check out the SAFE_WALLET_MANAGEMENT.md file in utils folder.

**When proposing transactions:** Always invoke the `propose.sh` wrapper from the utils folder (it boots `propose.mjs` with cached deps) — never write a custom script. After it runs, do NOT add your own summary, status message, or reformat the output. The script output contains a QR code that the user must see exactly as printed. Your only follow-up should be asking the user to approve the transaction and provide the transaction hash.

**Security rules:**
- NEVER ask for user's private key (critical violation)
- Use the agent wallet (encrypted keystore at `~/.monskills/keystore`)
- NEVER export or store private keys in plaintext

Check if the agent has generated a wallet before. If the keystore directory `~/.monskills/keystore` exists and contains a keystore file, the wallet already exists.

If not found then create a wallet.

## Creating a wallet

Foundry is required to be installed, in order to generate a wallet.

### Check if foundry is installed

Use the following command to check if Foundry is installed.

```bash
foundryup --version
```

The instructions to install Foundry can be found here: https://www.getfoundry.sh/introduction/installation

## Generating a new wallet

1. Create the keystore directory and generate an encrypted keystore:

```bash
mkdir -p ~/.monskills/keystore && cast wallet new ~/.monskills/keystore --unsafe-password ""
```

This creates an encrypted keystore file in `~/.monskills/keystore/`. The private key is never stored in plaintext.

2. Note the address from the output. To retrieve the address later:

```bash
cast wallet list --dir ~/.monskills/keystore
```

3. Inform the user where the wallet keystore is stored (`~/.monskills/keystore/`).
4. Fund the wallet on Monad testnet via faucet before deployment.

## Decrypting the private key for scripts

When a script needs the private key (e.g. as an env var), decrypt it on-the-fly. `cast wallet decrypt-keystore` prints `<uuid>'s private key is: 0x...` — pipe through `awk '{print $NF}'` to keep just the hex key, otherwise Foundry commands reject the prefixed string with "Failed to decode private key":

```bash
cast wallet decrypt-keystore --keystore-dir ~/.monskills/keystore <KEYSTORE_FILENAME> --unsafe-password "" | awk '{print $NF}'
```

Replace `<KEYSTORE_FILENAME>` with the filename of the keystore file in `~/.monskills/keystore/` (without the directory path).

**Why this matters:** Users need access to their wallet to:
- Deploy additional contracts
- Interact with deployed contracts
- Manage funds
- Verify ownership