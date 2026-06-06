# x402-payment

Agent-side USDC micropayments on **Arc Testnet** and **CrossFi**, wired into Hermes Agent as `tool.x402-payment`.

## What this is

- `hermes-additions/skills/x402-payment/SKILL.md` — the Hermes skill manifest.
- `hermes-additions/tools/x402_payment.py` — the implementation.

It adds an x402 payment path so Hermes can:
- check a USDC balance,
- pay a 402-protected resource,
- build and submit an EIP-3009 `TransferWithAuthorization` transfer,
- verify the on-chain `Transfer` event.

## Quick start

WARNING: THIS IS EDUCATIONAL CODE. TEST FIRST. DO NOT SEND REAL MONEY.

1. Copy the example env file:
   cp .env.example .env

2. Fill in real values in .env:
   X402_PRIVATE_KEY=
   X402_RPC_URL=https://your-rpc.example
   X402_CHAIN_ID=arc_testnet
   X402_USDC_CONTRACT=0x3600000000000000000000000000000000000000
   X402_PAYMENT_RECIPIENT=

3. Edit the skill to point at the tool:
   hermes config set tool.x402-payment /home/consumeobeydie/hermes-arc-x402/hermes-additions/tools/x402_payment.py

4. Restart Hermes, then use the skill:
   "Check my x402 USDC balance"
   "Send 0.05 USDC to the payment recipient"
   "Pay the 402 for https://example.com/api/data"

## Env vars

- X402_PRIVATE_KEY — hex private key (with or without 0x)
- X402_RPC_URL — JSON-RPC endpoint for the target chain
- X402_CHAIN_ID — arc, arc_testnet, crossfi, or mainnet
- X402_USDC_CONTRACT — override known contract addresses
- X402_PAYMENT_RECIPIENT — default payee

## Supported networks

- Arc
- Arc Testnet
- CrossFi
- Ethereum mainnet
- Other EVM chains via X402_CHAIN_ID + X402_USDC_CONTRACT

## Safety rails

- $1.00 max per request is hard-coded.
- 10-minute auth validity window.
- 60-second backdate for clock skew.
- Private keys never leave .env or the signing path.

## Verification

- Arc Explorer: https://testnet.arcscan.app
- CrossFi Explorer: https://explorer.crossfi.org
- USDC contract: https://github.com/centrehq/usdc-contracts

## License

MIT

## Disclaimer

This software is for educational and research purposes only.
Cryptocurrency transactions are irreversible.
Always test with faucet funds.
Never expose private keys.
Always inspect transactions before sending.
