#!/usr/bin/env python3
# Python | DARK OSINT Bot | python-telegram-bot v20 | Astha API
# Developed by GAUTAM YADAV
# deps: python-telegram-bot[job-queue]==20.7, requests

import json
import logging
import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ===== CONFIG =====
BOT_TOKEN = "8561834954:AAEsPWA_OXfQWzlfwvJ4oH6kEhrQNqfMwO8"
API_URL   = os.environ.get(
    "API_URL",
    "https://astha-9vd8.onrender.com/tapi-3a74390dd9a68a862b9d697124bb9e04",
)
BOT_NAME  = os.environ.get("BOT_NAME", "Develop by GAUTAM YADAV")

# Social Links & Support Contact
INSTAGRAM_USERNAME = "its_gautam.8"
TELEGRAM_CHANNEL_LINK = "https://t.me/+VkU0k932ZO1mqpRn"
SUPPORT_USERNAME = "its_gk121"

# 👑 Admin Telegram ID (Only for /addvip and /stats commands & Admin Logs)
ADMIN_ID = 1323479109

# 💳 UPI ID & Daily Limit
UPI_ID = "Gautamyadav08@nyes"
DAILY_FREE_LIMIT = 3
REFER_REWARD_CREDITS = 2  # 🎯 HAR REFER PAR 2 CREDITS/SEARCHES MILENGE
USERS_FILE = "users_data.json"
# =================

if not BOT_TOKEN:
    print("❌ BOT_TOKEN env variable missing. Exiting.")
    raise SystemExit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(BOT_NAME)


# ---------- Database Helpers ----------
def load_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error("Error loading data: %s", e)
    return {}

def save_data(data):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error("Error saving data: %s", e)

def get_user(user_id, referred_by=None):
    data = load_data()
    uid = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if uid not in data:
        data[uid] = {
            "verified": False,
            "is_premium": False,
            "searches_today": 0,
            "bonus_credits": 0,
            "referrals_count": 0,
            "referred_by": str(referred_by) if referred_by else None,
            "last_search_date": today
        }
        save_data(data)

    if data[uid].get("last_search_date") != today:
        data[uid]["searches_today"] = 0
        data[uid]["last_search_date"] = today
        save_data(data)

    return data[uid]

def update_user(user_id, key, value):
    data = load_data()
    uid = str(user_id)
    if uid in data:
        data[uid][key] = value
        save_data(data)


# ---------- Limit Check ----------
def check_user_limit(user_id):
    user = get_user(user_id)
    if not user.get("verified"):
        return False, "⚠️ Pehle Telegram Channel join aur Instagram follow karein!"
    
    if user.get("is_premium"):
        return True, "VIP"
    
    searches_today = user.get("searches_today", 0)
    bonus_credits = user.get("bonus_credits", 0)

    if searches_today < DAILY_FREE_LIMIT:
        return True, "FREE"
    elif bonus_credits > 0:
        return True, "BONUS"
    else:
        return False, (
            f"❌ <b>Daily Limit Reached ({DAILY_FREE_LIMIT}/{DAILY_FREE_LIMIT})!</b>\n\n"
            "Aapki aaj ki free limit khatam ho gayi hai aur aapke paas koi bonus credit nahi hai.\n\n"
            "💡 <b>Extra Searches chahiye?</b>\n"
            f"1. Dosto ko refer karein aur <b>+{REFER_REWARD_CREDITS} Free Credits</b> paayein!\n"
            "2. ya Premium plan kharidein (/pay)"
        )


# ---------- API Call & Clean ----------
def get_number_info(number):
    try:
        r = requests.get(API_URL, params={"Astha": number}, timeout=25)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                return data
        return None
    except Exception as e:
        log.error("API error: %s", e)
        return None

def extract_records(data):
    if not data: return []
    if isinstance(data.get("result"), dict):
        r = data["result"]
        if isinstance(r.get("data"), list): return r["data"]
        if isinstance(r.get("data"), dict): return [r["data"]]
    if isinstance(data.get("data"), list): return data["data"]
    if isinstance(data.get("data"), dict): return [data["data"]]
    return []

def dedupe(records):
    seen, out = set(), []
    for rec in records or []:
        if not isinstance(rec, dict): continue
        key = json.dumps({k: v for k, v in rec.items() if v}, sort_keys=True)
        if key in seen: continue
        seen.add(key)
        out.append(rec)
    return out

def prettify(data, number):
    records = dedupe(extract_records(data))
    if not records:
        return f"❌ <b>No records found</b>\n🔢 Number: <code>{number}</code>"

    header = f"🕵 <b>Develop by GAUTAM YADAV — Result</b>\n🔢 Number: <code>{number}</code>\n🧹 Unique: <b>{len(records)}</b>"
    parts = [header]
    for i, rec in enumerate(records, 1):
        block = [f"<b>━━━ Record #{i} ━━━</b>"]
        field_map = [
            ("name", "👤 Name"), ("fname", "👨 Father"), ("father_name", "👨 Father"),
            ("mobile", "📱 Mobile"), ("alt", "📞 Alt"), ("email", "📧 Email"),
            ("circle", "📡 Circle"), ("address", "🏠 Address")
        ]
        seen_labels = set()
        for key, label in field_map:
            if label in seen_labels: continue
            v = rec.get(key)
            if v is None or v == "" or str(v).lower() == "null": continue
            seen_labels.add(label)
            block.append(f"{label}: <code>{v}</code>")
        parts.append("\n".join(block))
    return "\n\n".join(parts)

def split_msg(text, size=4000):
    return [text[i:i + size] for i in range(0, len(text), size)]


# ---------- Keyboards ----------
def number_kb(number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Lookup Again", callback_data="again:" + number),
            InlineKeyboardButton("📄 JSON", callback_data="json:" + number),
        ]
    ])

def verification_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Telegram Channel", url=TELEGRAM_CHANNEL_LINK)],
        [InlineKeyboardButton("📸 Follow on Instagram", url=f"https://instagram.com/{INSTAGRAM_USERNAME}")],
        [InlineKeyboardButton("✅ Verify & Start", callback_data="check_follow")]
    ])

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("📱 Mobile Search"), KeyboardButton("🎁 Refer & Earn")],
        [KeyboardButton("🆔 Aadhaar (Coming Soon)"), KeyboardButton("💳 PAN (Coming Soon)")],
        [KeyboardButton("⭐ Buy Premium"), KeyboardButton("📞 Owner Contact")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_welcome_text(user_id):
    user = get_user(user_id)
    status = "⭐ VIP User (Unlimited)" if user.get("is_premium") else f"🆓 Free ({user.get('searches_today', 0)}/{DAILY_FREE_LIMIT} used today)"
    bonus = user.get("bonus_credits", 0)
    return (
        f"💀 <b>Develop by GAUTAM YADAV</b>\n"
        f"Status: <b>{status}</b>\n"
        f"🎁 Bonus Credits: <b>{bonus}</b> searches\n\n"
        "Niche diye gaye buttons se action select karein ya direct 10-digit mobile number bhejein.\n\n"
        "Commands:\n"
        "/start — Start/Reset bot\n"
        "/help — Show help menu\n"
        "/pay — Buy Premium Access\n"
        "/refer — Refer & Earn Link"
    )


# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    referred_by = None
    if context.args and context.args[0].isdigit():
        ref_id = context.args[0].strip()
        if ref_id != str(user_id):
            referred_by = ref_id

    user = get_user(user_id, referred_by=referred_by)

    if user.get("verified"):
        await update.message.reply_text(
            get_welcome_text(user_id), 
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        text = (
            f"⚠ <b>Must Join Channel & Follow Instagram First!</b>\n\n"
            f"Bot ka use karne ke liye pehle niche diye gaye <b>Telegram Channel</b> ko join karein aur <b>Instagram</b> par follow karein:\n\n"
            f"Dono karne ke baad <b>'✅ Verify & Start'</b> button par click karein."
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=verification_kb())

async def refer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    bot_username = context.bot.username
    
    refer_link = f"https://t.me/{bot_username}?start={user_id}"
    
    msg = (
        "🎁 <b>Refer & Earn Program</b>\n\n"
        f"Apne dosto ko refer karein aur har successful join par <b>+{REFER_REWARD_CREDITS} Bonus Credits (Extra Searches)</b> paayein!\n\n"
        f"🔗 <b>Aapka Referral Link:</b>\n<code>{refer_link}</code>\n\n"
        f"📊 <b>Aapki Stats:</b>\n"
        f"👥 Total Referrals: <b>{user.get('referrals_count', 0)}</b>\n"
        f"⚡ Total Bonus Credits: <b>{user.get('bonus_credits', 0)}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_menu_keyboard())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📖 Help — Develop by GAUTAM YADAV</b>\n\n"
        "• 10-digit number bhejo → full info\n"
        "• <code>/start</code> → Start/Reset bot\n"
        "• <code>/refer</code> → Refer & Earn credits\n"
        "• <code>/help</code> → Show help menu\n"
        "• <code>/pay</code> → Premium plans",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

async def pay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💎 <b>Develop by GAUTAM YADAV Premium Plans</b>\n\n"
        "✨ <b>Features:</b> Unlimited Daily Searches + Faster Speed\n\n"
        "💵 <b>Select Your Plan:</b>\n"
        "1️⃣ <b>Weekly Plan:</b> ₹19 / Week\n"
        "2️⃣ <b>Monthly Plan:</b> ₹59 / Month\n"
        "3️⃣ <b>Lifetime Plan:</b> ₹199 (Unlimited Access)\n\n"
        f"💳 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
        "<b>Payment Steps:</b>\n"
        "1. Upar di gayi UPI ID par plan ke hisab se payment karein.\n"
        "2. Payment screenshot/Transaction ID owner ko bhejein.\n"
        f"📩 <b>Support & Payment Verification:</b> @{SUPPORT_USERNAME}"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_menu_keyboard())

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Command to Add VIP User: /addvip <user_id>"""
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: <code>/addvip 1234567890</code>", parse_mode="HTML")
        return
    target_id = context.args[0].strip()
    
    data = load_data()
    if target_id not in data:
        data[target_id] = {"verified": True, "is_premium": True, "searches_today": 0, "bonus_credits": 0, "referrals_count": 0, "last_search_date": ""}
    else:
        data[target_id]["is_premium"] = True
        data[target_id]["verified"] = True
    save_data(data)
    
    await update.message.reply_text(f"✅ User <code>{target_id}</code> is now VIP!", parse_mode="HTML")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Command to check bot statistics: /stats"""
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()
    total_users = len(data)
    vip_users = sum(1 for u in data.values() if u.get("is_premium"))
    verified_users = sum(1 for u in data.values() if u.get("verified"))
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_searches = sum(
        u.get("searches_today", 0) 
        for u in data.values() 
        if u.get("last_search_date") == today
    )

    msg = (
        "📊 <b>Bot Usage Statistics</b>\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"✅ Verified Users: <b>{verified_users}</b>\n"
        f"⭐ VIP / Premium Users: <b>{vip_users}</b>\n"
        f"🔍 Today's Total Searches: <b>{today_searches}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    text_lower = text.lower()

    if text == "📱 Mobile Search":
        await update.message.reply_text("📱 Kripya 10-digit mobile number bhejein (e.g. <code>9876543210</code>)", parse_mode="HTML")
        return
    elif text == "🎁 Refer & Earn" or text_lower in ["refer", "referral", "/refer", "refer & earn"]:
        await refer_cmd(update, context)
        return
    elif text == "⭐ Buy Premium":
        await pay_cmd(update, context)
        return
    elif "aadhaar" in text_lower or text == "🆔 Aadhaar (Coming Soon)":
        await update.message.reply_text("⏳ <b>Aadhaar Details Service Coming Soon!</b>\nYeh feature jald hi available hoga.", parse_mode="HTML")
        return
    elif "pan" in text_lower or text == "💳 PAN (Coming Soon)":
        await update.message.reply_text("💳 <b>PAN Details Search:</b>\nKripya mobile number bhejein.", parse_mode="HTML")
        return
    elif text == "📞 Owner Contact":
        await update.message.reply_text(f"📞 <b>Owner & Support Contact:</b>\n\nTelegram: @{SUPPORT_USERNAME}\nInstagram: @{INSTAGRAM_USERNAME}", parse_mode="HTML")
        return

    # Extract digits from message
    extracted_number = "".join(ch for ch in text if ch.isdigit())

    # 🚫 Restricted Special Number Check
    if extracted_number == "9693675258":
        await update.message.reply_text("❌ <b>Papa ko search nhi karte</b>", parse_mode="HTML")
        return

    can_search, msg_or_type = check_user_limit(user_id)
    if not can_search:
        markup = verification_kb() if "Channel" in msg_or_type else None
        await update.message.reply_text(msg_or_type, parse_mode="HTML", reply_markup=markup)
        return

    await _handle(update, text, user_id, context, limit_type=msg_or_type)

async def _handle(update: Update, raw_text: str, user_id: int, context: ContextTypes.DEFAULT_TYPE, limit_type: str = "FREE"):
    number = "".join(ch for ch in raw_text if ch.isdigit())
    if len(number) != 10 or number[0] not in "6789":
        await update.message.reply_text("❌ Send exactly 10-digit Indian mobile (6/7/8/9 se start).")
        return

    # 📡 ADMIN NOTIFICATION LOG (Live Alert to Admin)
    user_info = update.effective_user
    username = f"@{user_info.username}" if user_info.username else "No Username"
    full_name = user_info.full_name or "Unknown"
    
    admin_log = (
        f"🔍 <b>New Search Logged!</b>\n\n"
        f"👤 <b>User:</b> {full_name} ({username})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"📱 <b>Searched Number:</b> <code>{number}</code>"
    )
    
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_log, parse_mode="HTML")
    except Exception as e:
        log.error("Failed to send search log to admin: %s", e)

    msg = await update.message.reply_text("⏳ Searching...")
    data = get_number_info(number)

    if not data:
        await msg.edit_text("❌ No data found!")
        return

    user = get_user(user_id)
    if not user.get("is_premium"):
        if limit_type == "FREE":
            update_user(user_id, "searches_today", user.get("searches_today", 0) + 1)
        elif limit_type == "BONUS":
            update_user(user_id, "bonus_credits", max(0, user.get("bonus_credits", 0) - 1))

    body = prettify(data, number)
    chunks = split_msg(body)
    for i, chunk in enumerate(chunks):
        if i == 0:
            await msg.edit_text(chunk, parse_mode="HTML", reply_markup=number_kb(number))
        else:
            await update.message.reply_text(chunk, parse_mode="HTML")

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data == "check_follow":
        user = get_user(user_id)
        if not user.get("verified"):
            update_user(user_id, "verified", True)
            
            referrer_id = user.get("referred_by")
            if referrer_id:
                referrer = get_user(referrer_id)
                new_credits = referrer.get("bonus_credits", 0) + REFER_REWARD_CREDITS
                new_count = referrer.get("referrals_count", 0) + 1
                
                update_user(referrer_id, "bonus_credits", new_credits)
                update_user(referrer_id, "referrals_count", new_count)
                
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"🎉 <b>New Referral Joined!</b>\n\nAapko <b>+{REFER_REWARD_CREDITS} Bonus Credits</b> mil gaye hain!",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    log.error("Failed to notify referrer: %s", e)

        await q.message.edit_text(
            "✅ <b>Verification Successful!</b>\n\n" + get_welcome_text(user_id), 
            parse_mode="HTML"
        )
        await q.message.reply_text("Main Menu:", reply_markup=get_main_menu_keyboard())


# ---------- Bot Startup Setup ----------
async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start or Reset Bot"),
        BotCommand("refer", "🎁 Refer & Earn Free Credits"),
        BotCommand("help", "📖 Help Menu"),
        BotCommand("pay", "💎 Buy Premium Access")
    ]
    await application.bot.set_my_commands(commands)


# ---------- Main Setup ----------
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("pay", pay_cmd))
    app.add_handler(CommandHandler("refer", refer_cmd))
    app.add_handler(CommandHandler("addvip", add_premium))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("💀 " + BOT_NAME + " is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
