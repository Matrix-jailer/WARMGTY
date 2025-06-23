# @Gen666Z

import sys
import os
import re
import subprocess
import time
import telegram
import random
import socket
import aiohttp
import tldextract
import asyncio
import json
import requests
import signal
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest, NetworkError, TimedOut
from tqdm import tqdm
from colorama import Fore, Style

# Configure logging
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths for persistent storage
DATA_DIR = "/opt/render/data"
LOCK_FILE = os.path.join(DATA_DIR, "playwright/.playwright_installed.lock")
REGISTERED_USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")
ADMIN_ACCESS_FILE = os.path.join(DATA_DIR, "adminaccess.json")
CREDIT_CODES_FILE = os.path.join(DATA_DIR, "creditcodes.json")
BAN_USERS_FILE = os.path.join(DATA_DIR, "banusers.json")
BOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "boardmessage.json")

# Initialize JSON files if they don't exist
def initialize_json_files():
    """Create empty JSON files if they don't exist to prevent warnings."""
    json_files = [
        REGISTERED_USERS_FILE,
        ADMIN_ACCESS_FILE,
        CREDIT_CODES_FILE,
        BAN_USERS_FILE,
        BOARD_MESSAGE_FILE
    ]
    for file_path in json_files:
        if not os.path.exists(file_path):
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                logger.info(f"Initialized empty JSON file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to initialize {file_path}: {e}")

initialize_json_files()

def install_playwright_once():
    """Install Playwright browsers once per deployment."""
    if not os.path.exists(LOCK_FILE):
        print("[+] Installing Playwright browsers...")
        try:
            os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
            subprocess.run(["playwright", "install", "chromium"], check=True)
            with open(LOCK_FILE, "w") as f:
                f.write("installed")
            print("[+] Playwright installation complete.")
        except Exception as e:
            print(f"[ERROR] Playwright installation failed: {e}")
    else:
        print("[✓] Playwright already installed. Skipping...")

# Run it once per deployment
install_playwright_once()

# Color definitions
merah = Fore.LIGHTRED_EX
putih = Fore.LIGHTWHITE_EX
hijau = Fore.LIGHTGREEN_EX
kuning = Fore.LIGHTYELLOW_EX
biru = Fore.LIGHTBLUE_EX
reset = Style.RESET_ALL

# Telegram Bot Configurations
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORWARD_CHANNEL_ID = "@mddj77273jdjdjd838383"

# Extended Lists
RELATED_PAGES = [
    "/",
    "/checkout",
    "/buynow",
    "/cart",
    "/payment",
    "/order",
    "/purchase",
    "/subscribe",
    "/confirm",
    "/billing",
    "/pay",
    "/transactions",
    "/order-summary",
    "/complete",
    "/shop",
    "/buy",
    "/proceed-to-checkout",
    "/payment-gateway",
    "/secure-checkout",
    "/order-confirmation",
    "/payment-processing",
    "/finalize-order"
]

PAYMENT_GATEWAYS = [
    "stripe",
    "paypal",
    "paytm",
    "razorpay",
    "square",
    "adyen",
    "braintree",
    "authorize.net",
    "klarna",
    "checkout.com",
    "shopify_payments",
    "worldpay",
    "2checkout",
    "amazon_pay",
    "apple_pay",
    "google_pay",
    "mollie",
    "opayo",
    "paddle"
]

CAPTCHA_PATTERNS = [
    r"g-recaptcha",
    r"data-sitekey",
    r"captcha",
    r"hcaptcha",
    r"protected by cloudflare",
    r"turnstile",
    r"arkose-labs",
    r"funcaptcha",
    r"geetest",
    r"recaptcha/api.js"
]

PLATFORM_KEYWORDS = {
    "woocommerce": "WooCommerce",
    "shopify": "Shopify",
    "magento": "Magento",
    "bigcommerce": "BigCommerce",
    "prestashop": "PrestaShop",
    "opencart": "OpenCart",
    "wix": "Wix",
    "squarespace": "Squarespace"
}

CARD_KEYWORDS = [
    "visa",
    "mastercard",
    "amex",
    "discover",
    "diners",
    "jcb",
    "unionpay",
    "maestro",
    "mir",
    "rupay",
    "cartasi",
    "hipercard"
]

THREE_D_SECURE_KEYWORDS = [
    "three_d_secure",
    "3dsecure",
    "acs",
    "acs_url",
    "acsurl",
    "redirect",
    "secure-auth",
    "challenge",
    "3ds",
    "3ds1",
    "3ds2",
    "tds",
    "tdsecure",
    "3d-secure",
    "three-d",
    "3dcheck",
    "3d-auth",
    "three-ds",
    "stripe.com/3ds",
    "m.stripe.network",
    "hooks.stripe.com/3ds",
    "paddle_frame",
    "paddlejs",
    "secure.paddle.com",
    "buy.paddle.com",
    "idcheck",
    "garanti.com.tr",
    "adyen.com/hpp",
    "adyen.com/checkout",
    "adyenpayments.com/3ds",
    "auth.razorpay.com",
    "razorpay.com/3ds",
    "secure.razorpay.com",
    "3ds.braintreegateway.com",
    "verify.3ds",
    "checkout.com/3ds",
    "checkout.com/challenge",
    "3ds.paypal.com",
    "authentication.klarna.com",
    "secure.klarna.com/3ds"
]

GATEWAY_KEYWORDS = {
    "stripe": ["stripe.com", "api.stripe.com/v1", "client_secret", "pi_", "stripe.js", "three_d_secure"],
    "paypal": ["paypal.com", "www.paypal.com", "paypal-sdk", "three_d_secure"],
    "braintree": ["braintreepayments.com", "client_token", "braintree.js", "three_d_secure"],
    "adyen": ["checkoutshopper-live.adyen.com", "adyen.js", "three_d_secure"],
    "authorize.net": ["authorize.net/gateway/transact.dll", "anet.js", "three_d_secure"],
    "square": ["squareup.com", "square.js", "three_d_secure"],
    "klarna": ["klarna.com", "klarna_checkout", "three_d_secure"],
    "checkout.com": ["checkout.com", "cko.js", "three_d_secure"],
    "razorpay": ["checkout.razorpay.com", "razorpay.js", "three_d_secure"],
    "paytm": ["securegw.paytm.in", "paytm.js", "three_d_secure"],
    "shopify_payments": ["shopify_payments", "checkout.shopify.com", "three_d_secure"],
    "worldpay": ["worldpay.com", "worldpay.js", "three_d_secure"],
    "2checkout": ["2checkout.com", "2co.js", "three_d_secure"],
    "amazon_pay": ["amazonpay.com", "amazonpay.js", "three_d_secure"],
    "apple_pay": ["apple.com", "apple-pay.js", "three_d_secure"],
    "google_pay": ["google.com", "googlepay.js", "three_d_secure"],
    "mollie": ["mollie.com", "mollie.js", "three_d_secure"],
    "opayo": ["opayo.com", "opayo.js", "three_d_secure"],
    "paddle": ["checkout.paddle.com", "checkout-service.paddle.com", "paddle.com/checkout", "paddle_button.js", "paddle.js"]
}

# Time conversion dictionary
TIME_CONVERSIONS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "year": 31536000
}

# Markdown Escaping
def escape_markdown(text, is_url=False):
    """Escape special Markdown characters, preserving URLs if specified."""
    if not text:
        return text
    if is_url:
        special_chars = r'[]()~`>#+-!|'  # Exclude dot
    else:
        special_chars = r'_*[]()~`>#+-.!|'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# JSON Utilities
def load_json(file_path):
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return {}
            data = json.loads(content)
            if not isinstance(data, dict):
                logger.error(f"Invalid JSON in {file_path}, expected dict but got {type(data)}")
                return {}
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

def save_json(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")

def load_registered_users():
    return load_json(REGISTERED_USERS_FILE)

def save_registered_users(users_data):
    save_json(REGISTERED_USERS_FILE, users_data)

def is_user_registered(user_id):
    registered = load_registered_users()
    return str(user_id) in registered

def register_user(user_id, update):
    registered = load_registered_users()
    if str(user_id) not in registered:
        registered[str(user_id)] = {
            "credits": 10,
            "join_date": time.time(),
            "username": f"@{escape_markdown(update.effective_user.username)}" if update.effective_user.username else f"User_{user_id}"
        }
        save_registered_users(registered)

def get_user_credits(user_id):
    registered = load_registered_users()
    return registered.get(str(user_id), {}).get("credits", 0)

def deduct_credit(user_id):
    registered = load_registered_users()
    if str(user_id) in registered and registered[str(user_id)]["credits"] > 0:
        registered[str(user_id)]["credits"] -= 1
        save_registered_users(registered)
        return True
    return False

def add_credit(user_id, amount, update):
    registered = load_registered_users()
    if str(user_id) in registered:
        registered[str(user_id)]["credits"] += amount
        save_registered_users(registered)
    else:
        registered[str(user_id)] = {
            "credits": amount,
            "join_date": time.time(),
            "username": f"@{escape_markdown(update.effective_user.username)}" if update.effective_user.username else f"User_{user_id}"
        }
        save_registered_users(registered)

def load_admin_access():
    return load_json(ADMIN_ACCESS_FILE)

def save_admin_access(data):
    save_json(ADMIN_ACCESS_FILE, data)

def is_admin(user_id):
    admin_access = load_admin_access()
    current_time = time.time()
    if str(user_id) in admin_access and admin_access[str(user_id)] > current_time:
        return True
    if str(user_id) in admin_access and admin_access[str(user_id)] <= current_time:
        del admin_access[str(user_id)]
        save_admin_access(admin_access)
    return False

def add_admin(user_id):
    admin_access = load_admin_access()
    admin_access[str(user_id)] = time.time() + 300  # 5 minutes expiration
    save_admin_access(admin_access)
    asyncio.create_task(remove_admin_access_after_delay(user_id))

async def remove_admin_access_after_delay(user_id):
    await asyncio.sleep(300)  # 5 minutes
    admin_access = load_admin_access()
    if str(user_id) in admin_access:
        del admin_access[str(user_id)]
        save_admin_access(admin_access)

def load_credit_codes():
    return load_json(CREDIT_CODES_FILE)

def save_credit_codes(data):
    save_json(CREDIT_CODES_FILE, data)

def load_ban_users():
    return load_json(BAN_USERS_FILE)

def save_ban_users(data):
    save_json(BAN_USERS_FILE, data)

def is_user_banned(user_id):
    ban_users = load_ban_users()
    current_time = time.time()
    if str(user_id) in ban_users:
        ban_info = ban_users.get(str(user_id))
        if ban_info.get("expires", 0) > current_time or ban_info.get("expires") == "permanent":
            return True
        else:
            del ban_users[str(user_id)]
            save_ban_users(ban_users)
    return False

def ban_user(user_id, reason, time_period):
    ban_users = load_ban_users()
    credits = get_user_credits(user_id)
    if time_period == "permanent":
        expires = "permanent"
    else:
        try:
            time_value = int(time_period[:-1])
            time_unit = time_period[-1]
            expires = time.time() + (time_value * TIME_CONVERSIONS.get(time_unit, 0))
        except (ValueError, IndexError):
            expires = time.time() + 86400  # Default to 1 day
    ban_users[str(user_id)] = {
        "id": str(user_id),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "credits_last_time": credits,
        "expires": expires
    }
    save_ban_users(ban_users)

def unban_user(user_id):
    ban_users = load_ban_users()
    if str(user_id) in ban_users:
        del ban_users[str(user_id)]
        save_ban_users(ban_users)

def load_board_message():
    data = load_json(BOARD_MESSAGE_FILE)
    return data.get("message", "🌟 *No message set!*").strip()

# URL Validation
async def validate_url(url):
    extracted = tldextract.extract(url)
    domain = extracted.registered_domain
    if not domain:
        return False, "Invalid URL: No valid domain found."

    try:
        socket.gethostbyname(domain)
    except socket.gaierror:
        return False, "Unresolvable DNS: Cannot connect to host."

    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=5) as resp:
                if resp.status == 429:
                    return False, "Rate limited (429). Try again later."
                if resp.status >= 400:
                    return False, f"HTTP Error: Status {resp.status}."
                cloudflare = "cloudflare" in dict(resp.headers).get("server", "").lower()
                if cloudflare:
                    return False, "Cloudflare protection detected. May not be bypassable."
                return True, "URL is accessible."
    except aiohttp.ClientError as e:
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# Web Scanning Functions

import cloudscraper
import ssl

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Mobile Safari/537.36',
]

def fetch_with_cloudscraper(url, max_retries=3):
    scraper = cloudscraper.create_scraper(
        browser={"custom": random.choice(USER_AGENTS)}
    )
    scraper.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    scraper.ssl_context = ssl.create_default_context()
    scraper.ssl_context.check_hostname = False
    scraper.ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=30)
            if response.ok and response.text.strip():
                return response.text
        except Exception as e:
            logger.warning(f"Cloudscraper failed for {url} (attempt {attempt+1}): {e}")
            time.sleep(1)
    return None

def analyze_html_content(html_content):
    result = {
        "payment_gateways": set(),
        "captcha": False,
        "cloudflare": False,
        "graphql": False,
        "platforms": set(),
        "card_support": set(),
        "is_3d_secure": False,
    }

    lower_html = html_content.lower()
    for gateway in PAYMENT_GATEWAYS:
        if gateway in lower_html:
            result["payment_gateways"].add(gateway.capitalize())
            if any(kw in lower_html for kw in THREE_D_SECURE_KEYWORDS):
                result["is_3d_secure"] = True

    if any(re.search(pattern, html_content, re.IGNORECASE) for pattern in CAPTCHA_PATTERNS):
        result["captcha"] = True

    result["graphql"] = "graphql" in lower_html
    result["cloudflare"] = "cloudflare" in lower_html

    for keyword, name in PLATFORM_KEYWORDS.items():
        if keyword in lower_html:
            result["platforms"].add(name)

    for card in CARD_KEYWORDS:
        if card in lower_html:
            result["card_support"].add(card.capitalize())

    return result


async def scan_page(url, browser, retries=3, timeout=10000):
    # Step 0: Try CloudScraper fetch
    html_content = fetch_with_cloudscraper(url)
    cloudscraper_result = analyze_html_content(html_content) if html_content else None

    playwright_result = {
        "payment_gateways": set(),
        "captcha": False,
        "cloudflare": False,
        "graphql": False,
        "platforms": set(),
        "card_support": set(),
        "is_3d_secure": False,
    }

    try:
        page = await browser.new_page(
            user_agent=random.choice(USER_AGENTS),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

        if not response:
            raise Exception("No response from page")

        content = await page.content()
        lower_content = content.lower()

        # Payment gateways
        for gateway in PAYMENT_GATEWAYS:
            if gateway in lower_content:
                playwright_result["payment_gateways"].add(gateway.capitalize())
                if any(kw in lower_content for kw in THREE_D_SECURE_KEYWORDS):
                    playwright_result["is_3d_secure"] = True

        # CAPTCHA
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in CAPTCHA_PATTERNS):
            playwright_result["captcha"] = True

        # Cloudflare
        playwright_result["cloudflare"] = "cloudflare" in lower_content

        # GraphQL
        playwright_result["graphql"] = "graphql" in lower_content

        # Platforms
        for keyword, name in PLATFORM_KEYWORDS.items():
            if keyword in lower_content:
                playwright_result["platforms"].add(name)

        # Card support
        for card in CARD_KEYWORDS:
            if card in lower_content:
                playwright_result["card_support"].add(card.capitalize())

        await page.close()

    except Exception as e:
        logger.warning(f"[Playwright] Skipped {url} due to error: {e}")
        try:
            await page.close()
        except:
            pass

    # Merge both results
    final_result = {
        "payment_gateways": set(),
        "captcha": False,
        "cloudflare": False,
        "graphql": False,
        "platforms": set(),
        "card_support": set(),
        "is_3d_secure": False,
    }

    if cloudscraper_result:
        final_result["payment_gateways"].update(cloudscraper_result["payment_gateways"])
        final_result["captcha"] |= cloudscraper_result["captcha"]
        final_result["cloudflare"] |= cloudscraper_result["cloudflare"]
        final_result["graphql"] |= cloudscraper_result["graphql"]
        final_result["platforms"].update(cloudscraper_result["platforms"])
        final_result["card_support"].update(cloudscraper_result["card_support"])
        final_result["is_3d_secure"] |= cloudscraper_result["is_3d_secure"]

    if playwright_result:
        final_result["payment_gateways"].update(playwright_result["payment_gateways"])
        final_result["captcha"] |= playwright_result["captcha"]
        final_result["cloudflare"] |= playwright_result["cloudflare"]
        final_result["graphql"] |= playwright_result["graphql"]
        final_result["platforms"].update(playwright_result["platforms"])
        final_result["card_support"].update(playwright_result["card_support"])
        final_result["is_3d_secure"] |= playwright_result["is_3d_secure"]

    return final_result
