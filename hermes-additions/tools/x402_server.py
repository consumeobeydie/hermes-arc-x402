#!/usr/bin/env python3
"""
x402 Demo Server — Arc Testnet
A simple HTTP server that requires x402 USDC payment to access premium market data.
The /premium/market endpoint returns simulated USDC market signals that the
Economy Engine uses to make dynamic vault strategy decisions.
"""
import json
import os
import time
import math
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

PAYMENT_RECIPIENT = os.getenv("X402_ADDRESS", "0x54b4B44749a95070560509B6Ec0be501665CcF63")
PAYMENT_AMOUNT = 0.001  # $0.001 USDC per request
PAYMENT_CHAIN = "arc_testnet"

def get_market_signal():
    """
    Simulates a market data oracle.
    Returns a signal that the Economy Engine uses to decide:
    - How large to make the mission budget
    - Whether to distribute yield
    - Whether to pause the economy loop
    """
    # Simulate a sine wave market cycle (period ~5 minutes)
    t = time.time()
    cycle = math.sin(t / 300 * 2 * math.pi)

    # Add some noise
    noise = random.uniform(-0.1, 0.1)
    signal = cycle + noise

    # Normalize to 0-100 score
    score = int((signal + 1) / 2 * 100)

    if score >= 70:
        action = "BULLISH"
        mission_multiplier = 1.5   # open larger missions
        yield_distribute = True
    elif score >= 40:
        action = "NEUTRAL"
        mission_multiplier = 1.0   # normal missions
        yield_distribute = False
    else:
        action = "BEARISH"
        mission_multiplier = 0.5   # smaller missions, conserve capital
        yield_distribute = False

    return {
        "timestamp": t,
        "score": score,
        "action": action,
        "mission_multiplier": mission_multiplier,
        "yield_distribute": yield_distribute,
        "recommended_budget_usdc": round(3.0 * mission_multiplier, 2),
        "source": "x402-arc-market-oracle-v1"
    }


class X402Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "server": "x402-arc-testnet-oracle"})
            return

        if self.path == "/premium/data" or self.path == "/premium/market":
            payment_header = self.headers.get("X-PAYMENT", "")
            if not payment_header:
                self.send_response(402)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Payment-Required", "true")
                self.end_headers()
                body = {
                    "error": "Payment Required",
                    "payTo": PAYMENT_RECIPIENT,
                    "amount": PAYMENT_AMOUNT,
                    "chain": PAYMENT_CHAIN,
                    "token": "USDC",
                    "description": "Premium Arc market oracle data — $0.001 USDC"
                }
                self.wfile.write(json.dumps(body).encode())
                print(f"[x402 server] 402 sent — payment required")
                return

            print(f"[x402 server] Payment proof received: {payment_header[:20]}...")
            signal = get_market_signal()
            self._respond(200, {
                "ok": True,
                "paid": True,
                "tx_hash": payment_header,
                "market": signal
            })
            return

        self._respond(404, {"error": "Not found"})

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode())

    def log_message(self, format, *args):
        print(f"[x402 server] {format % args}")


if __name__ == "__main__":
    port = int(os.getenv("X402_SERVER_PORT", 8402))
    print(f"[x402 server] Starting on http://localhost:{port}")
    print(f"[x402 server] Payment recipient: {PAYMENT_RECIPIENT}")
    print(f"[x402 server] Price: ${PAYMENT_AMOUNT} USDC per request")
    print(f"[x402 server] Endpoints: /health, /premium/market")
    HTTPServer(("", port), X402Handler).serve_forever()