import os
import subprocess
import logging
import asyncio
import random
import requests
import ssl
import cloudscraper
import re
import tldextract
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Persistent browser storage
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/data/playwright"
LOCK_FILE = "/opt/render/data/playwright/.playwright_installed.lock"

def install_playwright_once():
    if not os.path.exists(LOCK_FILE):
        try:
            print("[+] Installing Playwright Chromium...")
            subprocess.run(["playwright", "install", "chromium"], check=True)
            with open(LOCK_FILE, "w") as f:
                f.write("installed")
            print("[+] Playwright installation complete.")
        except Exception as e:
            print(f"[ERROR] Failed to install Playwright: {e}")
    else:
        print("[✓] Playwright already installed. Skipping...")

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
    # Step 0: Attempt CloudScraper before Playwright
    html_content = fetch_with_cloudscraper(url)
    if html_content:
        logger.info(f"✔ CloudScraper used for {url}")
        return analyze_html_content(html_content)

    result = {
        "payment_gateways": set(),
        "captcha": False,
        "cloudflare": False,
        "graphql": False,
        "platforms": set(),
        "card_support": set(),
        "is_3d_secure": False
    }
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=5) as resp:
                    if resp.status == 429:
                        delay = 2 ** attempt + random.uniform(0, 1)
                        logger.warning(f"429 for {url}, retrying after {delay:.2f}s ({attempt+1}/{retries})")
                        await asyncio.sleep(delay)
                        continue
                    if resp.status != 200:
                        logger.debug(f"Non-200 status for {url}: {resp.status}")
                        return result
                    result["cloudflare"] = "cloudflare" in dict(resp.headers).get("server", "").lower()

            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            try:
                response = await asyncio.wait_for(
                    page.goto(url, wait_until="domcontentloaded"),
                    timeout=timeout / 1000
                )
                if response and response.status == 429:
                    await page.close()
                    delay = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"429 for {url}, retrying after {delay:.2f}s ({attempt+1}/{retries})")
                    await asyncio.sleep(delay)
                    continue
                if response and response.status != 200:
                    logger.debug(f"Non-200 status for {url}: {response.status}")
                    await page.close()
                    return result
            except asyncio.TimeoutError:
                logger.warning(f"Timeout navigating to {url} on attempt {attempt+1}/{retries}")
                await page.close()
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
                    continue
                return result

            try:
                html_content = await asyncio.wait_for(page.content(), timeout=timeout / 1000)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching content for {url}")
                await page.close()
                return result

            soup = BeautifulSoup(html_content, 'html.parser')

            result["cloudflare"] = result["cloudflare"] or ("cloudflare" in response.headers.get("server", "").lower() if response else False)

            try:
                iframes = await page.query_selector_all("iframe")
                for iframe in iframes:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            frame_url = frame.url.lower()
                            if any(kw in frame_url for kw in THREE_D_SECURE_KEYWORDS):
                                result["is_3d_secure"] = True
                            frame_content = await asyncio.wait_for(frame.content(), timeout=timeout / 2000)
                            if any(kw in frame_content.lower() for kw in THREE_D_SECURE_KEYWORDS):
                                result["is_3d_secure"] = True
                    except (PlaywrightTimeoutError, asyncio.TimeoutError):
                        logger.debug(f"Timeout accessing iframe on {url}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error accessing iframe on {url}: {str(e)}")
                        continue
            except Exception as e:
                logger.debug(f"Error querying iframes on {url}: {str(e)}")

            for gateway in PAYMENT_GATEWAYS:
                if gateway in html_content.lower():
                    result["payment_gateways"].add(gateway.capitalize())
                    for kw in GATEWAY_KEYWORDS.get(gateway, []):
                        if kw in THREE_D_SECURE_KEYWORDS and kw in html_content.lower():
                            result["is_3d_secure"] = True

            if any(re.search(pattern, html_content, re.IGNORECASE) for pattern in CAPTCHA_PATTERNS):
                result["captcha"] = True

            result["graphql"] = "graphql" in html_content.lower()

            for keyword, name in PLATFORM_KEYWORDS.items():
                if keyword in html_content.lower():
                    result["platforms"].add(name)

            for card in CARD_KEYWORDS:
                if card in html_content.lower():
                    result["card_support"].add(card.capitalize())

            await page.close()
            return result
        except (PlaywrightTimeoutError, asyncio.TimeoutError) as e:
            logger.warning(f"Timeout error for {url}: {e}")
            if attempt < retries - 1:
                delay = 2 ** attempt + random.uniform(0, 1)
                await asyncio.sleep(delay)
                continue
        except Exception as e:
            logger.warning(f"Scan error for {url}: {e}")
            if attempt < retries - 1:
                delay = 2 ** attempt + random.uniform(0, 1)
                await asyncio.sleep(delay)
                continue
        finally:
            if 'page' in locals():
                await page.close()
    return result

async def scan_site_parallel(base_url, progress_callback=None):
    aggregated_results = {
        "payment_gateways": set(),
        "captcha": False,
        "cloudflare": False,
        "graphql": False,
        "platforms": set(),
        "card_support": set(),
        "is_3d_secure": False
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        full_urls = [base_url.rstrip("/") + page for page in RELATED_PAGES]

        sem = asyncio.Semaphore(2)
        async def limited_scan(url):
            async with sem:
                try:
                    return await asyncio.wait_for(
                        scan_page(url, browser, timeout=10000),
                        timeout=15
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Scan for {url} timed out after 15s, skipping")
                    return aggregated_results
                except Exception as e:
                    logger.warning(f"Error scanning {url}: {e}, skipping")
                    return aggregated_results

        completed_pages = 0
        total_pages = len(full_urls)
        tasks = [limited_scan(url) for url in full_urls]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=60 * len(full_urls) // len(tasks)
            )
            for page_results in results:
                if isinstance(page_results, dict):
                    aggregated_results["payment_gateways"].update(page_results["payment_gateways"])
                    aggregated_results["captcha"] |= page_results["captcha"]
                    aggregated_results["cloudflare"] |= page_results["cloudflare"]
                    aggregated_results["graphql"] |= page_results["graphql"]
                    aggregated_results["platforms"].update(page_results["platforms"])
                    aggregated_results["card_support"].update(page_results["card_support"])
                    aggregated_results["is_3d_secure"] |= page_results["is_3d_secure"]
                completed_pages += 1
                if progress_callback:
                    await progress_callback(completed_pages, total_pages)
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            logger.warning(f"Global scan timeout for {base_url}, returning partial results")
        finally:
            await browser.close()
    return aggregated_results

async def show_progress_bar(update: Update, context: ContextTypes.DEFAULT_TYPE, total_pages):
    message = await update.message.reply_text("**🌐 Checking website... [⬜⬜⬜⬜⬜] 0%**", parse_mode=ParseMode.MARKDOWN)
    bar_length = 5
    last_percent = -1

    async def update_progress(current, total):
        nonlocal last_percent
        current_percent = min(int((current / total) * 100), 100)
        if current_percent > last_percent:
            filled = int((current_percent / 100) * bar_length)
            progress = "🟧" * filled + "⬜" * (bar_length - filled) if current_percent < 100 else "🟩" * bar_length
            try:
                await message.edit_text(
                    f"**🌐 Checking website... [{progress}] {current_percent}%**",
                    parse_mode=ParseMode.MARKDOWN
                )
            except telegram.error.BadRequest as e:
                if "Message is not modified" not in str(e):
                    logger.error(f"Failed to update progress bar: {e}")
            except telegram.error.TimedOut:
                logger.warning("Timeout during progress update")
            last_percent = current_percent

    return message, update_progress

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_link = f"[@{escape_markdown(user.username)}](tg://user?id={user.id})" if user.username else f"User_{user.id}"
    keyboard = [
        [
            {"text": "📝 Register", "callback_data": "register"},
            {"text": "🔍 Check URL", "callback_data": "checkurl"}
        ],
        [
            {"text": "💰 Credits", "callback_data": "credits"},
            {"text": "👨‍💼 Admin", "callback_data": "admin"}
        ]
    ]
    reply_markup = create_inline_keyboard(keyboard)
    is_registered = is_user_registered(user.id)
    features = (
        "  - ✅ *Registered Successfully*\n"
        if is_registered else "  - ✅ *Register to get started*\n"
    ) + "  - 🔍 *Check URLs (1 credit per check)*\n  - 💰 *View your credits*"
    welcome_text = (
        f"🌟 **Welcome to Payment Gateway Scanner, {user_link}!** 🌟\n"
        f"🔧 **Analyze websites with ease!** Check payment gateways, platforms, 3D Secure, and more.\n"
        f"💡 **Features:**\n{features}\n"
        f"👉 **Click a button below to begin!** ⚡\n\n"
        f"⚡ **Contact: @Gen666Z** ⚡\n"
    )
    if update.message:
        message = await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        context.user_data["message_id"] = message.message_id
    else:
        try:
            await update.callback_query.edit_message_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Failed to edit message in start: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    keyboard = [
        [
            {"text": "📝 Register", "callback_data": "register"},
            {"text": "🔍 Check URL", "callback_data": "checkurl"}
        ],
        [
            {"text": "💰 Credits", "callback_data": "credits"},
            {"text": "👨‍💼 Admin", "callback_data": "admin"}
        ],
        [
            {"text": "🔙 Back", "callback_data": "back"}
        ]
    ]
    reply_markup = create_inline_keyboard(keyboard)

    if action := query.data:
        if action == "register":
            if is_user_banned(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 You are banned!**\n"
                        "📩 *Try to contact Owner to get Unban: @Gen666Z*\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in register (banned): {e}")
            elif is_user_registered(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 You are already registered!**\n"
                        f"💰 **Credits: {get_user_credits(user_id)}**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in register (already registered): {e}")
            else:
                register_user(user_id, update)
                try:
                    await query.edit_message_text(
                        "**✅ Registration Successful!**\n"
                        f"💰 **You received 10 credits! Current: 10**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in register (success): {e}")
        elif action == "checkurl":
            credits = get_user_credits(user_id)
            if is_user_banned(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 You are banned!**\n"
                        "📩 *Try to contact Owner to get Unban: @Gen666Z*\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in checkurl (banned): {e}")
            elif not is_user_registered(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 Please register first!**\n"
                        "📝 **Click 'Register' to get started.**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in checkurl (not registered): {e}")
            elif credits <= 0:
                try:
                    await query.edit_message_text(
                        "**💸 Out of Credits!**\n"
                        "🔴 **Your credits have run out!**\n"
                        "📩 **Contact Admin to recharge: @Gen666Z**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in checkurl (no credits): {e}")
            else:
                try:
                    await query.edit_message_text(
                        "**🔍 Enter URL to Check**\n"
                        f"💰 **Credits: {credits} (1 credit will be deducted)**\n"
                        "📝 **Send /url <url> (e.g., /url https://example.com)**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    context.user_data["awaiting_url"] = True
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in checkurl (prompt): {e}")
        elif action == "credits":
            credits = get_user_credits(user_id)
            if is_user_banned(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 You are banned!**\n"
                        "📩 **Try to contact Owner to get Unban: @Gen666Z*\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in credits (banned): {e}")
            elif not is_user_registered(user_id):
                try:
                    await query.edit_message_text(
                        "**🚫 Please register first!**\n"
                        "📝 **Click 'Register' to get started.**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in credits (not registered): {e}")
            else:
                try:
                    await query.edit_message_text(
                        f"**💰 Your Credits**\n"
                        f"🔢 **Available: {credits} credits**\n"
                        f"🔄 **1 credit per URL check**\n"
                        f"🔧 **Contact admin to recharge if needed!**\n\n",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        logger.error(f"Failed to edit message in credits (show): {e}")
        elif action == "admin":
            try:
                await query.edit_message_text(
                    "**👨‍💼 Contact Admin**\n"
                    "📩 **Reach out to @Gen666Z for support or recharges!**\n\n",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    logger.error(f"Failed to edit message in admin: {e}")
        elif action == "back":
            await start(update, context)

async def url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get("awaiting_url", False):
        return
    context.user_data["awaiting_url"] = False

    raw_text = update.message.text.strip()
    just_args = raw_text[len("/url"):].strip()
    if not just_args:
        await update.message.reply_text("**🚫 Usage: /url <url> (e.g., /url https://example.com)**", parse_mode=ParseMode.MARKDOWN)
        return

    url = just_args
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    if is_user_banned(user_id):
        await update.message.reply_text(
            "**🚫 You are banned!**\n"
            "📩 **Try to contact Owner to get Unban: @Gen666Z**\n\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
        )
        return
    if not is_user_registered(user_id):
        await update.message.reply_text(
            "**🚫 Please register first!**\n"
            "📝 **Click 'Register' in the menu to get started.**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if not deduct_credit(user_id):
        await update.message.reply_text(
            "**💸 Out of Credits!**\n"
            "🔴 **Your credits have run out!**\n"
            "📩 **Contact Admin to recharge: @Gen666Z**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    is_valid, message = await validate_url(url)
    if not is_valid:
        await update.message.reply_text(
            f"**❌ Invalid URL!**\n{escape_markdown(message)}\n\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_inline_keyboard([[{"text": "🔙 Back", "callback_data": "back"}]])
        )
        return

    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        try:
            start_time = time.time()
            progress_message, update_progress = await show_progress_bar(update, context, len(RELATED_PAGES))
            results = await scan_site_parallel(url, progress_callback=update_progress)
            processing_time = time.time() - start_time

            user = update.effective_user
            user_link = f"[@{escape_markdown(user.username)}](tg://user?id={user.id})" if user.username else f"User_{user.id}"
            credits_left = get_user_credits(user_id)
            gateways = ', '.join(sorted(results['payment_gateways'])) if results['payment_gateways'] else 'None found'
            platforms = ', '.join(sorted(results['platforms'])) if results['platforms'] else 'Unknown'
            cards = ', '.join(sorted(results['card_support'])) if results['card_support'] else 'None found'
            is_3d_secure_text = f"🔐 **3D Secure:** {'ENABLED' if results['is_3d_secure'] else 'DISABLED'}\n"

            result_text = (
                f"**🟢 Scan Results for {url}**\n"
                f"**⏱️ Time Taken:** {round(processing_time, 2)} seconds\n"
                f"**💳 Payment Gateways:** {escape_markdown(gateways)}\n"
                f"**🔒 Captcha:** {'Found ✅' if results['captcha'] else 'Not Found 🔥'}\n"
                f"**☁️ Cloudflare:** {'Found ✅' if results['cloudflare'] else 'Not Found 🔥'}\n"
                f"**📊 GraphQL:** {results['graphql']}\n"
                f"**🏬 Platforms:** {escape_markdown(platforms)}\n"
                f"**💵 Card Support:** {escape_markdown(cards)}\n"
                f"{is_3d_secure_text}"
                f"**💰 Credits Left:** {credits_left}\n"
                f"**🆔 Scanned by:** {user_link}\n"
            )
            try:
                await progress_message.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)
            except telegram.error.BadRequest as e:
                if "Message is not modified" not in str(e):
                    logger.error(f"Failed to edit final message: {e}")
                    await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            except telegram.error.TimedOut:
                logger.warning("Timeout during final message update")
                await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            try:
                await context.bot.send_message(
                    chat_id=FORWARD_CHANNEL_ID,
                    text=f"🔍 **URL Check Forwarded**\n{result_text}",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_notification=True
                )
            except Exception as e:
                logger.error(f"Error forwarding to channel: {e}")
            break
        except (NetworkError, TimedOut) as e:
            attempt += 1
            logger.warning(f"Network error occurred: {e}. Attempt {attempt+1}/{max_attempts}. Retrying in {2 ** attempt} seconds...")
            await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
            if attempt == max_attempts:
                error_text = f"**❌ Failed to check URL due to network issues: {escape_markdown(str(e))}**\n\n"
                try:
                    await progress_message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)
                except:
                    await update.message.reply_text(error_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error checking URL {url}: {e}")
            error_text = f"**❌ Error checking URL: {escape_markdown(str(e))}**\n\n"
            try:
                await progress_message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)
            except:
                await update.message.reply_text(error_text, parse_mode=ParseMode.MARKDOWN)
            break

    await start(update, context)

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text(
            "**🚫 You are banned!**\n"
            "📩 **Try to contact Owner to get Unban: @Gen666Z**\n\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
        )
        return

    raw_text = update.message.text.strip()
    just_args = raw_text[len("/redeem"):].strip()
    reply_markup = create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])

    if not just_args:
        await update.message.reply_text(
            "**📋 Usage: /redeem <code>**\n\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    else:
        credit_codes = load_credit_codes()
        if just_args not in credit_codes or credit_codes[just_args].get("used", True):
            await update.message.reply_text(
                "**📋 Usage: /redeem <code>**\n"
                "❌ **This code doesn't exist!**\n\n",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            credits = credit_codes[just_args]["credits"]
            add_credit(user_id, credits, update)
            credit_codes[just_args]["used"] = True
            save_credit_codes(credit_codes)
            await update.message.reply_text(
                f"**🎉 Redeemed {credits} credits successfully!**\n\n",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    await start(update, context)

async def xenex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenex command attempted by user {user_id}")
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) == 2 and args[1] == "true":
        add_admin(user_id)
        await update.message.reply_text(
            "**🛡️ Admin access granted for 5 minutes!**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
    logger.info(f"Xenex command processed for user {user_id}")

async def xenexgen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenexgen command attempted by user {user_id}")
    if not is_admin(user_id):
        logger.info(f"User {user_id} is not authorized for /xenexgen")
        return
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) != 3:
        await update.message.reply_text(
            "**❌ Usage: /xenexgen <code> <credit>**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    code, credit = args[1], int(args[2])
    credit_codes = load_credit_codes()
    credit_codes[code] = {"credits": credit, "used": False, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_credit_codes(credit_codes)
    await update.message.reply_text(
        f"**✅ Code {code} generated with {credit} credits!**\n\n"
        f"⚡ **Contact: @Gen666Z** ⚡\n",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Xenexgen command processed for user {user_id}")

async def xenexboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenexboard command attempted by user {user_id}")
    if not is_admin(user_id):
        logger.info(f"User {user_id} is not authorized for /xenexboard")
        return
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) == 2 and args[1] == "fire":
        message = load_board_message()
        if "No message set" in message:
            await update.message.reply_text(
                f"**❌ {message}**\n\n",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        registered_users = load_registered_users()
        for uid in registered_users:
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Could not send broadcast to {uid}: {e}")
        await update.message.reply_text(
            "**📤 Broadcast sent to all registered users!**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
    logger.info(f"Xenexboard command processed for user {user_id}")

async def xenexaddcredit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenexaddcredit command attempted by user {user_id}")
    if not is_admin(user_id):
        logger.info(f"User {user_id} is not authorized for /xenexaddcredit")
        return
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) != 3:
        await update.message.reply_text(
            "**❌ Usage: /xenexaddcredit <user_chat_id> <amount>**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_id, amount = args[1], int(args[2])
    add_credit(target_id, amount, update)
    await update.message.reply_text(
        f"**✅ Added {amount} credits to user {target_id}!**\n\n"
        f"⚡ **Contact: @Gen666Z** ⚡\n",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Xenexaddcredit command processed for user {user_id}")

async def xenexbanuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenexbanuser command attempted by user {user_id}")
    if not is_admin(user_id):
        logger.info(f"User {user_id} is not authorized for /xenexbanuser")
        return
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) < 3 or len(args) > 4:
        await update.message.reply_text(
            "**❌ Usage: /xenexbanuser <chat_id> <reason> [time_period] (e.g., 1minute, 4hour, permanent)**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_id, reason = args[1], args[2]
    time_period = args[3] if len(args) == 4 else "permanent"
    ban_user(target_id, reason, time_period)
    await update.message.reply_text(
        f"**✅ User {target_id} banned! Reason: {reason} | Duration: {time_period}**\n\n"
        f"⚡ **Contact: @Gen666Z** ⚡\n",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Xenexbanuser command processed for user {user_id}")

async def xenexunbanuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Xenexunbanuser command attempted by user {user_id}")
    if not is_admin(user_id):
        logger.info(f"User {user_id} is not authorized for /xenexunbanuser")
        return
    args = update.message.text.strip().split() if update.message and update.message.text else []
    if len(args) != 2:
        await update.message.reply_text(
            "**❌ Usage: /xenexunbanuser <chat_id>**\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_id = args[1]
    unban_user(target_id)
    await update.message.reply_text(
        f"**✅ User {target_id} unbanned!**\n\n"
        f"⚡ **Contact: @Gen666Z** ⚡\n",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Xenexunbanuser command processed for user {user_id}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")
    if update and update.message:
        try:
            await update.message.reply_text(
                f"**❌ An error occurred: {escape_markdown(str(context.error))}**\n"
                "📩 Please try again or contact @Gen666Z for support.\n",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text(
            "**🚫 You are banned!**\n"
            "📩 **Try to contact Owner to get Unban: @Gen666Z**\n\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_inline_keyboard([[{"text": "👨‍💼 Admin", "callback_data": "admin"}]])
        )

def create_inline_keyboard(buttons):
    keyboard = [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"]) for btn in row if isinstance(btn, dict)] for row in buttons if any(isinstance(btn, dict) for btn in row)]
    return InlineKeyboardMarkup(keyboard)

# Signal Handling
application = None

def handle_shutdown(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    if application:
        asyncio.run(application.shutdown())
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# Main
if __name__ == "__main__":
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("url", url_handler))
        application.add_handler(CommandHandler("redeem", redeem))
        application.add_handler(CommandHandler("xenex", xenex))
        application.add_handler(CommandHandler("xenexgen", xenexgen))
        application.add_handler(CommandHandler("xenexboard", xenexboard))
        application.add_handler(CommandHandler("xenexaddcredit", xenexaddcredit))
        application.add_handler(CommandHandler("xenexbanuser", xenexbanuser))
        application.add_handler(CommandHandler("xenexunbanuser", xenexunbanuser))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))
        application.add_error_handler(error_handler)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        sys.exit(1)
