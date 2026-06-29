#!/usr/bin/env python3
"""
OSINT Telegram Bot - Auto-restart, runs forever
Compatible with python-telegram-bot 22.x + Python 3.14
"""

import socket
import asyncio
import logging
import time
import sys
import whois
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─────────────────────────────────────────────────
# PASTE YOUR BOT TOKEN BELOW
BOT_TOKEN = "8325558482:AAHwj1ShurXIqeHOSNuTjHUgaoHo85fmxN0"
# ─────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

user_mode = {}

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Phone Lookup",       callback_data="mode_phone")],
        [InlineKeyboardButton("📧 Email / Username",   callback_data="mode_email")],
        [InlineKeyboardButton("🌐 Domain WHOIS",       callback_data="mode_whois")],
        [InlineKeyboardButton("👤 Telegram User Info", callback_data="mode_tguser")],
        [InlineKeyboardButton("💾 Leaked Data Search", callback_data="mode_leak")],
        [InlineKeyboardButton("ℹ️ Help",               callback_data="help")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome, *{user.first_name}*!\n\n"
        "🔍 *OSINT Bot* — Open Source Intelligence Toolkit\n\n"
        "Select a tool from the menu below:",
        parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Available Tools*\n\n"
        "📱 *Phone Lookup* — Carrier, region, line type\n"
        "📧 *Email/Username* — Breach status & presence\n"
        "🌐 *Domain WHOIS* — Registration & DNS details\n"
        "👤 *Telegram User Info* — Forward a message\n"
        "💾 *Leaked Data* — Search breach databases\n\n"
        "⚠️ *OPSEC:* Always use a VPN.\n\n"
        "/start — Return to main menu",
        parse_mode="Markdown", reply_markup=back_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id

    if data == "main_menu":
        user_mode.pop(uid, None)
        await query.edit_message_text(
            "🏠 *Main Menu* — Choose a tool:",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
    elif data == "help":
        await query.edit_message_text(
            "📖 *Available Tools*\n\n"
            "📱 Phone Lookup\n📧 Email/Username\n🌐 WHOIS\n👤 Telegram User\n💾 Leaked Data\n\n"
            "⚠️ Always practice good OPSEC.",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )
    elif data == "mode_phone":
        user_mode[uid] = "phone"
        await query.edit_message_text(
            "📱 *Phone Number Lookup*\n\nSend number in international format:\n`+1234567890`",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )
    elif data == "mode_email":
        user_mode[uid] = "email"
        await query.edit_message_text(
            "📧 *Email / Username Search*\n\nSend an email or @username:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )
    elif data == "mode_whois":
        user_mode[uid] = "whois"
        await query.edit_message_text(
            "🌐 *Domain WHOIS Lookup*\n\nSend a domain:\n`example.com`",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )
    elif data == "mode_tguser":
        user_mode[uid] = "tguser"
        await query.edit_message_text(
            "👤 *Telegram User Info*\n\nForward a message from the target, or send their @username:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )
    elif data == "mode_leak":
        user_mode[uid] = "leak"
        await query.edit_message_text(
            "💾 *Leaked Data Search*\n\nSend an email or username:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    mode = user_mode.get(uid)
    if not mode:
        await update.message.reply_text("Please choose a tool first:", reply_markup=main_menu_keyboard())
        return
    msg = update.message
    if   mode == "phone":  await handle_phone(msg)
    elif mode == "email":  await handle_email(msg)
    elif mode == "whois":  await handle_whois(msg)
    elif mode == "tguser": await handle_tguser(msg)
    elif mode == "leak":   await handle_leak(msg)

async def handle_phone(msg):
    text = msg.text.strip()
    await msg.reply_text("🔍 Looking up phone number...")
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone as tz
        phone    = phonenumbers.parse(text)
        if not phonenumbers.is_valid_number(phone):
            await msg.reply_text("❌ Invalid. Use: `+1234567890`", parse_mode="Markdown", reply_markup=back_keyboard())
            return
        country  = geocoder.description_for_number(phone, "en")
        carrier_ = carrier.name_for_number(phone, "en")
        tzones   = tz.time_zones_for_number(phone)
        fmt_intl = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        fmt_e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
        type_map = {0:"Fixed Line",1:"Mobile",2:"Fixed/Mobile",3:"Toll Free",4:"Premium Rate",6:"VOIP",7:"Personal",99:"Unknown"}
        line_type= type_map.get(phonenumbers.number_type(phone), "Unknown")
        await msg.reply_text(
            f"📱 *Phone Report*\n{'─'*28}\n"
            f"📞 *Number:* `{fmt_intl}`\n"
            f"🔢 *E164:* `{fmt_e164}`\n"
            f"🌐 *Country:* {country or 'Unknown'}\n"
            f"📡 *Carrier:* {carrier_ or 'Unknown'}\n"
            f"📶 *Line Type:* {line_type}\n"
            f"🕐 *Timezone:* {', '.join(tzones) or 'Unknown'}\n\n"
            f"🔗 *Check further:*\n"
            f"• [OSINT Rocks](https://osint.rocks/)\n"
            f"• [TrueCaller Bot](https://t.me/TrueCaller_Z_Bot)\n"
            f"• [GetContact Bot](https://t.me/getcontact_real_bot)",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Phone error: {e}")
        await msg.reply_text(f"❌ Error: {e}", reply_markup=back_keyboard())

async def handle_email(msg):
    text     = msg.text.strip()
    is_email = "@" in text and "." in text.split("@")[-1]
    await msg.reply_text("🔍 Searching...")
    if is_email:
        await msg.reply_text(
            f"📧 *Email Investigation*\n{'─'*28}\n"
            f"📮 *Email:* `{text}`\n\n"
            f"🔗 *Resources:*\n"
            f"• [HaveIBeenPwned](https://haveibeenpwned.com/account/{text})\n"
            f"• [Epieos](https://epieos.com/?q={text}&t=email)\n"
            f"• [Hunter.io](https://hunter.io/email-verifier/{text})\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={text})\n"
            f"• [IntelX](https://intelx.io/?s={text})\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [LeakCheck Bot](https://t.me/LeakCheckBot)\n"
            f"• [All In One Leaks](https://t.me/AllInOneLeaksBOT)\n"
            f"• [Email Leaks Bot](https://t.me/EmailLeaks_bot)",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )
    else:
        username = text.lstrip("@")
        await msg.reply_text(
            f"👤 *Username Investigation*\n{'─'*28}\n"
            f"🔎 *Username:* `{username}`\n\n"
            f"🔗 *Resources:*\n"
            f"• [WhatsMyName](https://whatsmyname.app/?q={username})\n"
            f"• [Namechk](https://namechk.com/{username})\n"
            f"• [Telegram](https://t.me/{username})\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [Maigret OSINT Bot](https://t.me/maigret_osint_bot)\n"
            f"• [LeakCheck Bot](https://t.me/LeakCheckBot)",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )

async def handle_whois(msg):
    domain = msg.text.strip().lower().replace("https://","").replace("http://","").split("/")[0]
    await msg.reply_text(f"🔍 Running WHOIS on `{domain}`...", parse_mode="Markdown")
    try:
        loop = asyncio.get_event_loop()
        w    = await loop.run_in_executor(None, whois.whois, domain)
        def fmt(val):
            if val is None: return "N/A"
            if isinstance(val, list): val = val[0]
            if isinstance(val, datetime): return val.strftime("%Y-%m-%d")
            return str(val)
        try: ip = socket.gethostbyname(domain)
        except: ip = "N/A"
        ns = ", ".join(list(w.name_servers)[:2]) if w.name_servers else "N/A"
        await msg.reply_text(
            f"🌐 *WHOIS: {domain}*\n{'─'*28}\n"
            f"🏢 *Registrar:* {fmt(w.registrar)}\n"
            f"📅 *Created:* {fmt(w.creation_date)}\n"
            f"⏰ *Expires:* {fmt(w.expiration_date)}\n"
            f"🖥 *IP:* `{ip}`\n"
            f"🌍 *Country:* {fmt(w.country)}\n"
            f"📡 *Name Servers:* {ns}\n\n"
            f"🔗 *Investigate further:*\n"
            f"• [ViewDNS](https://viewdns.info/whois/?domain={domain})\n"
            f"• [VirusTotal](https://www.virustotal.com/gui/domain/{domain})\n"
            f"• [Shodan](https://www.shodan.io/search?query={domain})",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"WHOIS error: {e}")
        await msg.reply_text(f"❌ WHOIS failed: {e}", reply_markup=back_keyboard())

def estimate_account_age(user_id: int) -> str:
    ranges = [
        (100000000,   "~2013-2014 (Very old)"),
        (500000000,   "~2014-2016 (Old)"),
        (1000000000,  "~2016-2018"),
        (2000000000,  "~2018-2019"),
        (4000000000,  "~2019-2020"),
        (6000000000,  "~2020-2021"),
        (8000000000,  "~2021-2022"),
        (10000000000, "~2022-2023"),
        (float("inf"),"~2023+ (Recent)"),
    ]
    for threshold, label in ranges:
        if user_id < threshold:
            return label
    return "Unknown"

async def handle_tguser(msg):
    if msg.forward_origin:
        try:
            from telegram import MessageOriginUser
            if isinstance(msg.forward_origin, MessageOriginUser):
                user    = msg.forward_origin.sender_user
                uid     = user.id
                uname   = f"@{user.username}" if user.username else "N/A"
                premium = "✅ Yes" if getattr(user, "is_premium", False) else "❌ No"
                await msg.reply_text(
                    f"👤 *Telegram User Info*\n{'─'*28}\n"
                    f"🆔 *User ID:* `{uid}`\n"
                    f"👤 *Name:* {user.first_name or ''} {user.last_name or ''}\n"
                    f"📛 *Username:* {uname}\n"
                    f"🤖 *Is Bot:* {'✅' if user.is_bot else '❌'}\n"
                    f"⭐ *Premium:* {premium}\n"
                    f"📅 *Account Age Est.:* {estimate_account_age(uid)}\n\n"
                    f"🔗 *Investigate further:*\n"
                    f"• [Creation Date Bot](https://t.me/creationdatebot)\n"
                    f"• [UserInfo Bot](https://t.me/userinfobot)\n"
                    f"• [TelegramDB](https://www.telegramdb.org/search)\n"
                    f"• [TGScan](https://t.me/tgscanrobot)",
                    parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
                )
                return
        except Exception as e:
            logger.error(f"TG user error: {e}")
        await msg.reply_text(
            "⚠️ User has *Forward Privacy* enabled — info is hidden.\n\n"
            "Try [UserInfo Bot](https://t.me/userinfobot) instead.",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )
    elif msg.text and msg.text.startswith("@"):
        username = msg.text.strip().lstrip("@")
        await msg.reply_text(
            f"👤 *Username Lookup*\n{'─'*28}\n"
            f"📛 *Username:* @{username}\n\n"
            f"🔗 *Investigate:*\n"
            f"• [Direct Profile](https://t.me/{username})\n"
            f"• [Web View](https://web.telegram.org/k/#@{username})\n"
            f"• [Username→ID Bot](https://t.me/username_to_id_bot)\n"
            f"• [Creation Date Bot](https://t.me/creationdatebot)\n"
            f"• [SangMata Bot](https://t.me/SangMata_beta_bot)",
            parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True
        )
    else:
        await msg.reply_text(
            "ℹ️ *How to use:*\n\n1️⃣ *Forward* a message from the target here\n2️⃣ Or send their `@username`",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

async def handle_leak(msg):
    query    = msg.text.strip()
    is_email = "@" in query
    await msg.reply_text("🔍 Checking breach databases...")
    base = (
        f"💾 *Leaked Data Search*\n{'─'*28}\n"
        f"🔎 *Query:* `{query}`\n"
        f"{'📧 Email' if is_email else '👤 Username'}\n\n"
        f"🔗 *Check manually:*\n"
    )
    if is_email:
        base += (
            f"• [HaveIBeenPwned](https://haveibeenpwned.com/account/{query})\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={query})\n"
            f"• [IntelX](https://intelx.io/?s={query})\n"
            f"• [BreachDirectory](https://breachdirectory.org/)\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [LeakCheck Bot](https://t.me/LeakCheckBot)\n"
            f"• [All In One Leaks](https://t.me/AllInOneLeaksBOT)\n"
            f"• [Email Leaks Bot](https://t.me/EmailLeaks_bot)\n"
            f"• [Data Leaks Bot](https://t.me/dataLeaks_bot)"
        )
    else:
        base += (
            f"• [IntelX](https://intelx.io/?s={query})\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={query})\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [LeakCheck Bot](https://t.me/LeakCheckBot)\n"
            f"• [All In One Leaks](https://t.me/AllInOneLeaksBOT)"
        )
    await msg.reply_text(base, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "tguser"
    await handle_tguser(update.message)

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ──────────────────────────────────────────────
# FOREVER LOOP — AUTO RESTART ON ANY CRASH
# ──────────────────────────────────────────────

def main():
    restart_count = 0
    while True:
        try:
            if restart_count == 0:
                print("🤖 OSINT Bot starting...")
            else:
                print(f"🔄 Restarting bot (attempt #{restart_count})...")

            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help",  help_command))
            app.add_handler(CallbackQueryHandler(button_handler))
            app.add_handler(MessageHandler(filters.FORWARDED, forward_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
            app.add_error_handler(error_handler)

            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            sys.exit(0)

        except Exception as e:
            restart_count += 1
            wait = min(30, restart_count * 5)
            logger.error(f"Bot crashed: {e}. Restarting in {wait}s...")
            print(f"⚠️  Crashed: {e}")
            print(f"⏳ Restarting in {wait} seconds...")
            time.sleep(wait)

if __name__ == "__main__":
    main()