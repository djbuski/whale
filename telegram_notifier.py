import requests
from datetime import datetime
import re

# --- User Configuration ---
BOT_TOKEN = "7793455671:AAEATJBJSsnIbeUBNQ3CLopjkyskksoYExI"
CHAT_IDS = [
    "6652200721",
    "7267070155",
    "6453753862"
]
# --------------------------

# Incrementally building template - Step 3: Adding token info, USD value, time, and link
MESSAGE_TEMPLATE = {
    "BUY": """🟢 *BUY ALERT* 🟢
━━━━━━━━━━━━━━━━━
• *Wallet:* {wallet_name}
• *Wallet Address:* `{wallet_address}`
━━━━━━━━━━━━━━━━━
• *Token Information:*
    • *Token Name:* {token_name}
    • *Token Symbol:* {token_symbol}
    • *Token Address:* `{token_address}`
━━━━━━━━━━━━━━━━━
• *Type:* {tx_type}
• *Amount:* *{amounts}*
• *Value:* ${usd_value}
• *Time:* {timestamp}
━━━━━━━━━━━━━━━━━
[View Transaction](https://solscan.io/tx/{tx_hash})
""",
    "SELL": """🔴 *SELL ALERT* 🔴
━━━━━━━━━━━━━━━━━
• *Wallet:* {wallet_name}
• *Wallet Address:* `{wallet_address}`
━━━━━━━━━━━━━━━━━
• *Token Information:*
    • *Token Name:* {token_name}
    • *Token Symbol:* {token_symbol}
    • *Token Address:* `{token_address}`
━━━━━━━━━━━━━━━━━
• *Type:* {tx_type}
• *Amount:* *{amounts}*
• *Value:* ${usd_value}
• *Time:* {timestamp}
━━━━━━━━━━━━━━━━━
[View Transaction](https://solscan.io/tx/{tx_hash})
"""
}

ERROR_TEMPLATE = """⚠️ *SYSTEM ALERT* ⚠️
━━━━━━━━━━━━━━━━━
• *Error:* {error_message}
• *Time:* {timestamp}"""

def escape_markdown_v2(text: str) -> str:
    """Helper function to escape special characters for Telegram MarkdownV2."""
    escape_chars = r"[_*[\]()~`>#+\-=|{}.!]"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))

def send_telegram_notification(wallet_name, wallet_address, token_name, token_symbol, token_address, tx_type, amounts, usd_value, timestamp, tx_hash):
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        error_msg = "Bot token not configured"
        send_error_notification(error_msg)
        return False
    if not CHAT_IDS:
        error_msg = "No chat IDs configured"
        send_error_notification(error_msg)
        return False
    if tx_type.upper() not in ["BUY", "SELL"]:
        error_msg = f"Invalid transaction type: {tx_type}"
        send_error_notification(error_msg)
        return False

    escaped_wallet_name = escape_markdown_v2(wallet_name)
    # wallet_address and token_address are in backticks, no general escaping needed for them here.
    escaped_token_name = escape_markdown_v2(token_name)
    escaped_token_symbol = escape_markdown_v2(token_symbol)
    escaped_tx_type = escape_markdown_v2(tx_type.upper())
    escaped_amounts = escape_markdown_v2(amounts)
    escaped_usd_value = escape_markdown_v2(usd_value)
    escaped_timestamp = escape_markdown_v2(timestamp)
    # tx_hash is part of a URL, no escaping needed for the URL itself.

    message_text = MESSAGE_TEMPLATE[tx_type.upper()].format(
        wallet_name=escaped_wallet_name,
        wallet_address=wallet_address, 
        token_name=escaped_token_name,
        token_symbol=escaped_token_symbol,
        token_address=token_address,
        tx_type=escaped_tx_type,
        amounts=escaped_amounts,
        usd_value=escaped_usd_value,
        timestamp=escaped_timestamp,
        tx_hash=tx_hash
    )
    return _send_telegram_message(message_text)

def send_error_notification(error_message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    escaped_error_message = escape_markdown_v2(error_message)
    escaped_timestamp = escape_markdown_v2(timestamp)
    message_text = ERROR_TEMPLATE.format(
        error_message=escaped_error_message,
        timestamp=escaped_timestamp
    )
    return _send_telegram_message(message_text)

def _send_telegram_message(message_text):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    all_sent_successfully = True
    for chat_id in CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False # Enable preview for Solscan link
        }
        try:
            response = requests.post(send_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"Notification sent to Chat ID {chat_id}. Text:\n{message_text}")
        except Exception as e:
            print(f"Failed to send to Chat ID {chat_id}: {str(e)}. Text:\n{message_text}")
            try:
                error_text_plain = f"Error sending detailed notification to {chat_id}. Original error: {str(e)}. Please check bot logs."
                fallback_payload = {"chat_id": chat_id, "text": error_text_plain}
                requests.post(send_url, data=fallback_payload, timeout=5)
                print(f"Sent plain text fallback error message to {chat_id}")
            except Exception as fallback_e:
                print(f"Failed to send plain text fallback error message to {chat_id}: {fallback_e}")
            all_sent_successfully = False
    return all_sent_successfully

if __name__ == "__main__":
    print("Sending FULLY RESTORED test notifications with MarkdownV2 escaping...")
    send_telegram_notification(
        wallet_name="Test Whale (Zaga_Baby!)",
        wallet_address="So1Whale-AdDress.EXAMPLExxxxxxxxxxxxxxxxx",
        token_name="Jupiter Coin (JUP)",
        token_symbol="J.U.P*!",
        token_address="JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        tx_type="BUY",
        amounts="+1,250,000.50!",
        usd_value="1,187,575.00",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        tx_hash="5exampleTransactionHashxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    )
    send_error_notification("Fully restored test error message with: * _ . ! ` [ ] ( ) ~ > # + - = | { } ")

