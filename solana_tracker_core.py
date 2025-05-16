import requests
import json
import time
from datetime import datetime, timezone, timedelta

# Import the Telegram notification function and relevant configs
from telegram_notifier import send_telegram_notification, BOT_TOKEN as TELEGRAM_BOT_TOKEN, CHAT_IDS as TELEGRAM_CHAT_IDS

# --- User Configuration ---
HELIUS_API_KEY = "c7a485f8-360c-4a25-96eb-189d8f0fa97e"

# Define the list of wallets to monitor with their custom names
# You can add, remove, or edit wallets in this list.
# Each wallet is a dictionary with "address" and "name".
WALLETS_TO_MONITOR = [
    {"address": "GzyMwXjNNB6UjUHs48SsEeWCueFZyPFbjFjJxvy5MHmp", "name": "Zagababy"},
    {"address": "5ow9M5AZUDUm3p3PAeBYMA8g2n65fKRMrfdbqEyE2b6U", "name": "Volt baby"},
    {"address": "2cyYy2zPyThCJAVcD4JhqnTWnsTVSVJe55Gw3NrPKBf8", "name": "Aza baby"},
    {"address": "3cBB2ZyoNy8YEquSSzR2Rpggp9vcrfz4NcbCKHp7BzvT", "name": "Sugar"},
    {"address": "GmM5UFm8xu6TnZD7avwYcQ1zq25hD5yvHfYyAksHu9vB", "name": "Haley"},
    {"address": "3wj7ajoFkDWru2m3icULwe2JrCPht6f93NkNWKJwyBoG", "name": "Kiddo"},
    {"address": "52i9pMBBqAqkbSNrMffH5H6mxVvFVMevLbY3HFAeTXFM", "name": "Jonze"}
]
# --------------------------

HELIUS_API_BASE_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Keep track of the last seen transaction signature for each wallet
# Format: { "wallet_address": "last_signature_string" }
LAST_SEEN_SIGNATURES = {}

# --- Configuration for Degen Activity ---
EARLY_INVESTMENT_THRESHOLD_USD = 80000
EARLY_INVESTMENT_MAX_AGE_HOURS = 24
LARGE_TRADE_THRESHOLD_USD = 10000
STABLECOIN_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT"
}
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"

def get_wallet_balances(wallet_address: str):
    """Fetches token balances for a given Solana wallet address using Helius."""
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
        "params": [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
    }
    try:
        response = requests.post(HELIUS_API_BASE_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "result" in data and "value" in data["result"]:
            token_accounts = data["result"]["value"]
            balances = []
            for account in token_accounts:
                try:
                    info = account["account"]["data"]["parsed"]["info"]
                    balances.append({"mint": info["mint"], "uiAmountString": info["tokenAmount"]["uiAmountString"], "decimals": info["tokenAmount"]["decimals"]})
                except KeyError as e:
                    print(f"Skipping account due to missing data: {e} in account {account}")
            return balances
        elif "error" in data: print(f"Error (get_wallet_balances) for {wallet_address}: {data['error']}"); return None
        else: print(f"Unexpected response (get_wallet_balances) for {wallet_address}: {data}"); return None
    except Exception as e: print(f"Request failed (get_wallet_balances) for {wallet_address}: {e}"); return None

def get_transaction_details(signature: str):
    """Fetches detailed information for a given transaction signature."""
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
    }
    try:
        response = requests.post(HELIUS_API_BASE_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "result" in data and data["result"] is not None: return data["result"]
        elif "error" in data: 
            error_msg = data['error']
            print(f"Error (getTransactionDetails) for {signature}: {error_msg}"); 
            return None
        else: return None
    except Exception as e: print(f"Request failed (getTransactionDetails) for {signature}: {e}"); return None

def get_recent_transaction_signatures(wallet_address: str, limit: int = 10, before_signature: str = None):
    """Fetches recent transaction signatures for a given Solana wallet address."""
    params_obj = {"limit": limit}
    if before_signature:
        params_obj["before"] = before_signature
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
        "params": [wallet_address, params_obj]
    }
    try:
        response = requests.post(HELIUS_API_BASE_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "result" in data and data["result"] is not None:
            return [tx["signature"] for tx in data["result"]]
        elif "error" in data: 
            error_msg = data['error']
            print(f"Error (getSignaturesForAddress) for {wallet_address}: {error_msg}"); 
            return []
        else: print(f"No signatures found for {wallet_address}: {data}"); return []
    except Exception as e: print(f"Request failed (getSignaturesForAddress) for {wallet_address}: {e}"); return []

def get_asset_details_helius(mint_address: str):
    """Fetches asset details including creation time using Helius getAsset."""
    payload = {"jsonrpc": "2.0", "id": "helius-asset-details", "method": "getAsset", "params": {"id": mint_address}}
    try:
        response = requests.post(HELIUS_API_BASE_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "result" in data and data["result"] is not None:
            asset_data = data["result"]
            created_at_str = asset_data.get("created_at")
            name = asset_data.get("content", {}).get("metadata", {}).get("name", "Unknown")
            symbol = asset_data.get("content", {}).get("metadata", {}).get("symbol", "UNKN")
            created_at_dt = None
            if created_at_str:
                try:
                    if isinstance(created_at_str, (int, float)):
                        created_at_dt = datetime.fromtimestamp(created_at_str / 1000 if created_at_str > 1e11 else created_at_str, timezone.utc)
                    elif isinstance(created_at_str, str):
                        created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except ValueError as ve: print(f"Error parsing created_at for mint {mint_address}: {ve}")
            return {"name": name, "symbol": symbol, "created_at": created_at_dt, "raw_created_at": created_at_str}
        elif "error" in data: 
            error_msg = data['error'] # This was already correct due to assignment
            print(f"Error (get_asset_details_helius) for {mint_address}: {error_msg}"); 
            return None
        else: print(f"No asset details found for {mint_address}"); return None
    except Exception as e: print(f"Request failed (get_asset_details_helius) for {mint_address}: {e}"); return None

def get_token_price_usd(mint_address: str, transaction_time_unix: int = None):
    """Placeholder: Fetches token price in USD. Returns a mock price."""
    if mint_address == WRAPPED_SOL_MINT: return 150.0
    if mint_address in STABLECOIN_MINTS: return 1.0
    return 0.01 # Default mock price

def analyze_transaction_for_degen_activity(tx_details, wallet_address):
    """Analyzes a single transaction for degen activity."""
    events = []
    if not tx_details or tx_details.get("meta", {}).get("err") is not None: return events
    block_time_unix = tx_details.get("blockTime")
    if not block_time_unix: return events
    transaction_time_dt = datetime.fromtimestamp(block_time_unix, timezone.utc)
    tx_hash = tx_details.get("transaction", {}).get("signatures", [None])[0]

    events.append({
        "type": "General Wallet Movement",
        "token_symbol": "N/A", "token_mint": "N/A", "amount": "N/A", "usd_value": "N/A",
        "timestamp": transaction_time_dt.isoformat(), "tx_hash": tx_hash
    })

    pre_balances = tx_details.get("meta", {}).get("preTokenBalances", [])
    post_balances = tx_details.get("meta", {}).get("postTokenBalances", [])

    for post_bal in post_balances:
        owner = str(post_bal.get("owner"))
        if owner != wallet_address: continue
        mint = str(post_bal.get("mint"))
        post_amount = float(post_bal.get("uiTokenAmount", {}).get("uiAmountString", "0"))
        pre_amount = 0.0
        for pre_bal in pre_balances:
            if str(pre_bal.get("owner")) == owner and str(pre_bal.get("mint")) == mint:
                pre_amount = float(pre_bal.get("uiTokenAmount", {}).get("uiAmountString", "0"))
                break
        amount_changed = post_amount - pre_amount
        if abs(amount_changed) < 1e-9: continue

        token_details = get_asset_details_helius(mint)
        token_symbol = token_details["symbol"] if token_details else mint[:6]
        token_created_at = token_details["created_at"] if token_details else None
        price_usd = get_token_price_usd(mint, block_time_unix)
        usd_value_changed = abs(amount_changed) * price_usd

        if token_created_at and amount_changed > 0:
            age_of_token = transaction_time_dt - token_created_at
            if age_of_token < timedelta(hours=EARLY_INVESTMENT_MAX_AGE_HOURS) and usd_value_changed > EARLY_INVESTMENT_THRESHOLD_USD:
                events.append({
                    "type": "Early Large Investment",
                    "token_symbol": token_symbol, "token_mint": mint, "amount": f"{amount_changed:+.2f}", 
                    "usd_value": f"{usd_value_changed:.2f}",
                    "timestamp": transaction_time_dt.isoformat(), "tx_hash": tx_hash,
                    "token_age_hours": round(age_of_token.total_seconds() / 3600, 2)
                })
        
        if usd_value_changed > LARGE_TRADE_THRESHOLD_USD:
            trade_type = "Token Received" if amount_changed > 0 else "Token Sent"
            is_early_investment = any(e["type"] == "Early Large Investment" and e["token_mint"] == mint for e in events)
            if not (is_early_investment and amount_changed > 0):
                 events.append({
                    "type": f"Large Trade ({trade_type})",
                    "token_symbol": token_symbol, "token_mint": mint, "amount": f"{amount_changed:+.2f}", 
                    "usd_value": f"{usd_value_changed:.2f}",
                    "timestamp": transaction_time_dt.isoformat(), "tx_hash": tx_hash
                })
    return events

def process_wallet_transactions(wallet_info: dict):
    """Processes transactions for a single wallet and sends notifications."""
    global LAST_SEEN_SIGNATURES
    wallet_address = wallet_info["address"]
    wallet_name = wallet_info["name"]
    last_seen_signature_for_wallet = LAST_SEEN_SIGNATURES.get(wallet_address)

    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time_str}] Checking transactions for wallet: {wallet_name} ({wallet_address})...")
    
    signatures_to_check = []
    current_batch = get_recent_transaction_signatures(wallet_address, limit=20) # Increased limit for active wallets
    if not current_batch: 
        print(f"No transactions found for {wallet_name} ({wallet_address}) in this poll.")
        return

    for sig in current_batch:
        if sig == last_seen_signature_for_wallet: break
        signatures_to_check.append(sig)
    
    if not signatures_to_check:
        if last_seen_signature_for_wallet != current_batch[0]:
            LAST_SEEN_SIGNATURES[wallet_address] = current_batch[0]
        print(f"No new transactions for {wallet_name} ({wallet_address}).")
        return

    print(f"Found {len(signatures_to_check)} new signature(s) for {wallet_name} ({wallet_address}).")
    for sig in reversed(signatures_to_check): # Process oldest new first
        print(f"Processing signature: {sig} for wallet: {wallet_name}")
        details = get_transaction_details(sig)
        if details:
            detected_events = analyze_transaction_for_degen_activity(details, wallet_address)
            for event in detected_events:
                # Corrected f-string for event type
                print(f"Event for {wallet_name}: {event['type']}") 
                notif_token_symbol = event.get("token_symbol", "N/A")
                notif_token_mint = event.get("token_mint", "N/A")
                notif_amount = event.get("amount", "N/A")
                notif_usd_value = event.get("usd_value", "N/A")
                notif_timestamp = event.get("timestamp")
                notif_tx_hash = event.get("tx_hash")
                notif_type = event['type'] # This was already correct
                # Corrected f-string for token_age_hours
                if event.get("token_age_hours") is not None:
                    notif_type += f" (Token Age: {event['token_age_hours']}h)"
                
                send_telegram_notification(
                    wallet_name=wallet_name,
                    wallet_address=wallet_address,
                    tx_type=notif_type,
                    tokens=f"{notif_token_symbol} ({notif_token_mint})" if notif_token_mint != "N/A" else "N/A",
                    amounts=str(notif_amount),
                    usd_value=str(notif_usd_value),
                    timestamp=notif_timestamp,
                    tx_hash=notif_tx_hash
                )
        else: print(f"Could not fetch details for signature: {sig} (Wallet: {wallet_name})")
    LAST_SEEN_SIGNATURES[wallet_address] = signatures_to_check[0]
    print(f"Updated LAST_SEEN_SIGNATURE for {wallet_name} ({wallet_address}) to: {LAST_SEEN_SIGNATURES[wallet_address]}")

if __name__ == "__main__":
    print("Starting Solana Wallet Tracker Core Bot...")
    # Check if Telegram Bot Token is configured and if there are Chat IDs to send to
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or not TELEGRAM_CHAT_IDS:
        print("CRITICAL ERROR: Telegram BOT_TOKEN is not configured or CHAT_IDS list is empty in telegram_notifier.py!")
        if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
            print("- Please configure BOT_TOKEN.")
        if not TELEGRAM_CHAT_IDS:
            print("- Please ensure CHAT_IDS list in telegram_notifier.py contains at least one Chat ID.")
        print("Please configure them before running the bot.")
        exit()

    # Initialize last seen signatures for all monitored wallets
    print("Initializing last seen signatures for all wallets...")
    for wallet_data in WALLETS_TO_MONITOR:
        addr = wallet_data["address"]
        name = wallet_data["name"]
        if addr not in LAST_SEEN_SIGNATURES:
            initial_signatures = get_recent_transaction_signatures(addr, limit=1)
            if initial_signatures:
                LAST_SEEN_SIGNATURES[addr] = initial_signatures[0]
                print(f"Initial LAST_SEEN_SIGNATURE for {name} ({addr}): {initial_signatures[0]}")
            else:
                LAST_SEEN_SIGNATURES[addr] = None # No transactions yet
                print(f"No initial transactions found for {name} ({addr}). Will start fresh.")

    print(f"\n--- Initiating Transaction Monitoring for {len(WALLETS_TO_MONITOR)} wallet(s) (Ctrl+C to stop) ---")
    POLL_INTERVAL_SECONDS = 1 # Can be adjusted
    try:
        while True:
            for wallet_to_check in WALLETS_TO_MONITOR:
                process_wallet_transactions(wallet_to_check)
                time.sleep(5) # Small delay between checking different wallets to avoid hitting rate limits too quickly
            print(f"\n--- Completed a full cycle of wallet checks. Waiting {POLL_INTERVAL_SECONDS}s for next cycle. ---")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nTransaction monitoring stopped by user.")
    print("Note: USD value calculation and memecoin identification are simplified/placeholders.")

