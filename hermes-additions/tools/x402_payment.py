import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ValidationError
from eth_account import Account
from eth_utils import to_checksum_address, to_bytes, to_hex, event_abi_to_log_topic

load_dotenv()

# Preferred USDC values are provided for Arc, CrossFi, and a generic mainnet fallback.
# These are the token contract addresses for each supported network in this scaffold.
X402_USDC_CONTRACTS = {
    "crossfi": "0x8aC7A9381B424488e3b8c482289133F37E128B0c",
    "mainnet": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "arc": "0x3600000000000000000000000000000000000000",
    "arc_testnet": "0x3600000000000000000000000000000000000000",
}

# EIP-3009 TransferWithAuthorization signature
EIP3009_SELECTOR = Web3.keccak(text="TransferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)")[:4]
TRANSFER_EVENT_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()

# Default RPC URLs keyed by chain name; overridden by X402_RPC_URL env var.
X402_DEFAULT_RPCS = {
    "arc_testnet": "https://rpc.arc.testnet.circle.com",
}

X402_CHAIN_IDS = {
    "crossfi": 3726,
    "mainnet": 1,
    "arc": 5042002,
    "arc_testnet": 1516,
}


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing env: {name}")
    return value


def _build_w3() -> Web3:
    chain = os.environ.get("X402_CHAIN_ID", "crossfi").lower()
    chain_id = X402_CHAIN_IDS.get(chain)
    if chain_id is None:
        raise RuntimeError(f"Unsupported X402_CHAIN_ID: {chain}")
    # Use X402_RPC_URL from env, falling back to a known default for this chain
    rpc = os.environ.get("X402_RPC_URL") or X402_DEFAULT_RPCS.get(chain)
    if not rpc:
        raise RuntimeError(
            f"No RPC URL for chain '{chain}'. Set X402_RPC_URL or add an entry to X402_DEFAULT_RPCS."
        )
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to RPC: {rpc}")
    return w3, chain_id


def _account() -> Account:
    pk = _get_env("X402_PRIVATE_KEY")
    if not pk.startswith("0x"):
        pk = "0x" + pk
    return Account.from_key(pk)


def _usdc_address(w3: Web3, chain_id: int) -> str:
    chain_name = os.environ.get("X402_CHAIN_ID", "crossfi").lower()
    address = X402_USDC_CONTRACTS.get(chain_name)
    if address is None:
        raise RuntimeError(f"No known USDC contract for chain: {chain_name}")
    return to_checksum_address(address)


def _usdc_decimals() -> int:
    return 6


def _normalize_usdc(amount: float) -> int:
    return int(amount * (10 ** _usdc_decimals()))


def _verify_usdc_transfer(w3: Web3, usdc_address: str, from_address: str, to_address: str, value: int, confirmations: int = 1) -> dict:
    """
    Query the USDC contract for a matching Transfer event.
    """
    latest = w3.eth.block_number
    contract = w3.eth.contract(address=usdc_address, abi=[
        {"anonymous": False, "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ], "name": "Transfer", "type": "event"}
    ])
    from_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    from_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    to_topic = Web3.keccak(text=Web3.to_hex(Web3.solidity_keccak(["address", "address"], [from_address, to_address]))[2:]).hex()
    # Relax matching: filter on 100 block window from latest
    filter_params = {
        "fromBlock": max(0, latest - 100),
        "toBlock": "latest",
        "address": usdc_address,
    }
    logs = w3.eth.get_logs(filter_params)
    for log in logs:
        if len(log["topics"]) < 3:
            continue
        # topic 1 = from, topic 2 = to
        if log["topics"][1].hex() != Web3.to_hex(Web3.solidity_keccak(["address"], [from_address]))[2:]:
            continue
        if log["topics"][2].hex() != Web3.to_hex(Web3.solidity_keccak(["address"], [to_address]))[2:]:
            continue
        # data is the uint256 value as 32-byte hex
        actual_value = int(log["data"].hex(), 16)
        if actual_value == value:
            return {
                "ok": True,
                "block_number": log["blockNumber"],
                "tx_hash": log["transactionHash"].hex(),
            }
    return {"ok": False, "reason": "no_matching_transfer_event"}


def x402_status(w3: Web3 = None) -> dict:
    """
    Return wallet status: address, chain, and USDC balance.
    """
    if w3 is None:
        w3, chain_id = _build_w3()
    else:
        _, chain_id = _build_w3()
    acct = _account()
    sender = to_checksum_address(acct.address)
    usdc_address = _usdc_address(w3, chain_id)
    contract = w3.eth.contract(address=usdc_address, abi=[
        {"constant": True, "inputs": [{"name": "account", "type": "address"}],
         "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
    ])
    balance = contract.functions.balanceOf(sender).call()
    decimals = _usdc_decimals()
    return {
        "ok": True,
        "address": sender,
        "chain_id": chain_id,
        "usdc_contract": usdc_address,
        "usdc_balance": balance / (10 ** decimals),
        "raw_balance": str(balance),
    }


def x402_send_native(to: str, amount: float) -> str:
    to = to_checksum_address(to)
    w3, chain_id = _build_w3()
    acct = _account()
    sender = to_checksum_address(acct.address)

    nonce = w3.eth.get_transaction_count(sender)
    value = w3.to_wei(float(amount), "ether")
    tx = {
        "chainId": chain_id,
        "nonce": nonce,
        "to": to,
        "value": value,
        "gas": 21000,
    }
    gas_price = w3.eth.gas_price
    tx["gasPrice"] = gas_price
    tx["maxFeePerGas"] = gas_price
    tx["maxPriorityFeePerGas"] = 0

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status = "confirmed" if receipt.status == 1 else "reverted"
    return json.dumps({
        "ok": receipt.status == 1,
        "tx_hash": tx_hash.hex(),
        "chain_id": chain_id,
        "from": sender,
        "to": to,
        "amount": amount,
        "gas_price_gwei": round(gas_price / 1e9, 2),
        "status": status,
        "block_number": receipt.blockNumber,
    })


def x402_send_usdc_eip3009(to: str, amount: float) -> str:
    """
    Send USDC on supported networks using EIP-3009 TransferWithAuthorization.

    Returns a JSON object with either:
    - "ok": true, "tx_hash", "raw_authorization" when signed txn is sent, or
    - "ok": true, "raw_authorization" when only offchain authorization is requested.
    """
    to = to_checksum_address(to)
    w3, chain_id = _build_w3()
    acct = _account()
    sender = to_checksum_address(acct.address)

    usdc_address = _usdc_address(w3, chain_id)

    # USDC has 6 decimals
    decimals = _usdc_decimals()
    value = _normalize_usdc(amount)

    # Safety cap: max $1.00 per request
    if amount > 1.00:
        raise ValueError("Amount exceeds safety limit of $1.00 USDC")

    now = int(time.time())
    valid_after = now - 60
    valid_before = now + 600
    nonce_bytes = to_bytes(os.urandom(32))

    # Build EIP-3009 calldata
    encoded = (
        EIP3009_SELECTOR
        + Web3.codec.encode_abi(
            ["address", "address", "uint256", "uint256", "uint256", "bytes32"],
            [Web3.to_checksum_address(sender), to, value, valid_after, valid_before, nonce_bytes],
        )
    )

    # Sign authorization with EIP-191
    signed = acct.sign_unsigned_eip712_message(
        {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            },
            "domain": {
                "name": "USD Coin",
                "version": "2",
                "chainId": chain_id,
                "verifyingContract": usdc_address,
            },
            "primaryType": "TransferWithAuthorization",
            "message": {
                "from": sender,
                "to": to,
                "value": value,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "nonce": nonce_bytes,
            },
        }
    )

    v, r, s = signed.v, signed.r, signed.s
    tx_data = encoded + Web3.codec.encode_abi(["uint8", "bytes32", "bytes32"], [v, r, s])

    tx = {
        "chainId": chain_id,
        "nonce": w3.eth.get_transaction_count(sender),
        "to": usdc_address,
        "data": tx_data,
        "gas": 160000,
    }
    gas_price = w3.eth.gas_price
    tx["gasPrice"] = gas_price
    tx["maxFeePerGas"] = gas_price
    tx["maxPriorityFeePerGas"] = 0

    signed_tx = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    result = {
        "ok": receipt.status == 1,
        "tx_hash": tx_hash.hex(),
        "chain_id": chain_id,
        "from": sender,
        "to": to,
        "amount": amount,
        "contract": usdc_address,
        "gas_price_gwei": round(gas_price / 1e9, 2),
        "raw_authorization": to_hex(tx_data),
        "status": "confirmed" if receipt.status == 1 else "reverted",
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
    }

    # Optional verification: confirm matching Transfer event
    if receipt.status == 1:
        verification = _verify_usdc_transfer(w3, usdc_address, sender, to, value)
        result["verified"] = verification.get("ok", False)
        result["verification"] = verification
    return json.dumps(result)


if __name__ == "__main__":
    recipient = os.environ.get("X402_PAYMENT_RECIPIENT", "0x" + "0" * 40)
    print(x402_send_usdc_eip3009(recipient, 0.01))
