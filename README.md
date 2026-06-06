# hermes-arc-x402

> Autonomous x402 payment agent for Arc Testnet — built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

[![Built on Hermes Agent](https://img.shields.io/badge/Hermes_Agent-Nous_Research-635BFF?style=flat-square)](https://github.com/NousResearch/hermes-agent)
[![Arc Testnet](https://img.shields.io/badge/Arc-Testnet-blue?style=flat-square)](https://testnet.arcscan.app)
[![x402 Protocol](https://img.shields.io/badge/x402-Payment_Protocol-orange?style=flat-square)](https://x402.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## What is this?

**hermes-arc-x402** teaches [Hermes Agent](https://github.com/NousResearch/hermes-agent) to autonomously make x402 micropayments on [Arc Testnet](https://testnet.arcscan.app) using USDC.

When Hermes encounters an HTTP 402 Payment Required response, it:
1. Parses the payment requirements
2. Signs a USDC authorization (EIP-3009)
3. Retries the request with the payment proof
4. Returns the response — no human intervention needed

Inspired by [Circle's agentic payments guide](https://www.circle.com/blog/build-agentic-systems-for-high-frequency-sub-cent-transactions), built for Hermes.

---

## Architecture

```text
User Request
    │
    ▼
Hermes Agent
    │
    ▼
HTTP 402? ──► x402-payment Skill ──► x402_payment Tool
    │                                       │
    │                              ┌───────┴────────┐
    │                              │  USDC / EVM     │
    │                              │  via web3.py    │
    │                              └───────┬────────┘
    │                                      │
    └──────────────────────────────────────┘
                    Retry + X-PAYMENT
```

Components:
- `hermes-additions/skills/x402-payment/SKILL.md` — when/why to pay, safety rules
- `hermes-additions/tools/x402_payment.py` — USDC balance, EIP-3009 signing, retry proof
- `.env` — private key, RPC URL, chain config, contract overrides

---

## Installation

```bash
git clone https://github.com/consumeobeydie/hermes-arc-x402.git
cd hermes-arc-x402
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Fill in `.env`:
   ```bash
   X402_PRIVATE_KEY=
   X402_RPC_URL=https://your-rpc.example
   X402_CHAIN_ID=arc_testnet
   X402_USDC_CONTRACT=0x3600000000000000000000000000000000000000
   X402_PAYMENT_RECIPIENT=
   ```

3. Hook the tool into Hermes:
   ```bash
   hermes config set tool.x402-payment /home/consumeobeydie/hermes-arc-x402/hermes-additions/tools/x402_payment.py
   ```

4. Restart Hermes.

---

## Usage

Once configured, ask Hermes naturally:

- "Check my x402 USDC balance"
- "Send 0.05 USDC to the payment recipient"
- "Pay the 402 for https://example.com/api/data"

The tool will:
- validate addresses,
- check balance,
- build and submit an EIP-3009 `TransferWithAuthorization`,
- wait for confirmation,
- verify the on-chain `Transfer` event,
- return a receipt.

---

## Env vars

| Key | Required | Description |
|-----|----------|-------------|
| `X402_PRIVATE_KEY` | Yes | Hex private key (with or without `0x`) |
| `X402_RPC_URL` | Yes | JSON-RPC endpoint for the target chain |
| `X402_CHAIN_ID` | Yes | `arc`, `arc_testnet`, `crossfi`, or `mainnet` |
| `X402_USDC_CONTRACT` | No | Override the known USDC contract address |
| `X402_PAYMENT_RECIPIENT` | No | Default payee for transfers |

---

## Supported networks

- Arc
- Arc Testnet
- CrossFi
- Ethereum mainnet
- Any EVM chain via `X402_CHAIN_ID` + `X402_USDC_CONTRACT`

---

## Safety rails

- $1.00 max per request (hard-coded)
- 10-minute auth validity window
- 60-second backdate for clock skew
- Private keys never leave `.env` or the signing path
- Receipt verification via on-chain `Transfer` event

---

## Verification

- Arc Explorer: https://testnet.arcscan.app
- CrossFi Explorer: https://explorer.crossfi.org
- USDC contracts: https://github.com/centrehq/usdc-contracts

---

## Disclaimer

This software is for educational and research purposes only.
Cryptocurrency transactions are irreversible.
Always test with faucet funds.
Never expose private keys.
Always inspect transactions before sending.
