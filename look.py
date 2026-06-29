#!/usr/bin/env python3
"""
OSINT Telegram Bot
Features: Phone lookup, Email/Username search, WHOIS, Telegram user info, Leaked data search
"""

import os
import re
import json
import socket
import asyncio
import logging
import whois
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN ="8765028098:AAEEvfZHtaBEq6t-wxWPqSYlvPP22sE1EF4"

# Conversation states
WAITING_INPUT = 1

# Current mode per user
user_mode = {}

# ──────────────────────────────────────────────
# MENUS
# ──────────────────────────────────────────────

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Phone Lookup",      callback_data="mode_phone")],
        [InlineKeyboardButton("📧 Email / Username",  callback_data="mode_email")],
        [InlineKeyboardButton("🌐 Domain WHOIS",      callback_data="mode_whois")],
        [InlineKeyboardButton("👤 Telegram User Info",callback_data="mode_tguser")],
        [InlineKeyboardButton("💾 Leaked Data Search",callback_data="mode_leak")],
        [InlineKeyboardButton("ℹ️ Help",              callback_data="help")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ])

# ──────────────────────────────────────────────
# HANDLERS — COMMANDS
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Welcome, *{user.first_name}*!\n\n"
        "🔍 *OSINT Bot* — Open Source Intelligence Toolkit\n\n"
        "Select a tool from the menu below:"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Available Tools*\n\n"
        "📱 *Phone Lookup* — Carrier, region, line type info\n"
        "📧 *Email/Username* — Check breach status & presence\n"
        "🌐 *Domain WHOIS* — Registration & DNS details\n"
        "👤 *Telegram User Info* — Forward a message to get user data\n"
        "💾 *Leaked Data* — Search known breach databases\n\n"
        "⚠️ *OPSEC Reminder:* Use a VPN and sock account when running investigations.\n\n"
        "Use /start to return to the main menu."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

# ──────────────────────────────────────────────
# CALLBACKS — BUTTON PRESSES
# ──────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    if data == "main_menu":
        user_mode.pop(uid, None)
        await query.edit_message_text(
            "🏠 *Main Menu* — Choose a tool:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    elif data == "help":
        text = (
            "📖 *Available Tools*\n\n"
            "📱 *Phone Lookup* — Carrier, region, line type\n"
            "📧 *Email/Username* — Breach & presence check\n"
            "🌐 *Domain WHOIS* — Registration details\n"
            "👤 *Telegram User Info* — Forward a message to get data\n"
            "💾 *Leaked Data* — Search breach databases\n\n"
            "⚠️ Always practice good OPSEC."
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    elif data == "mode_phone":
        user_mode[uid] = "phone"
        await query.edit_message_text(
            "📱 *Phone Number Lookup*\n\nSend a phone number in international format:\n`+1234567890`",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif data == "mode_email":
        user_mode[uid] = "email"
        await query.edit_message_text(
            "📧 *Email / Username Search*\n\nSend an email address or username to investigate:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif data == "mode_whois":
        user_mode[uid] = "whois"
        await query.edit_message_text(
            "🌐 *Domain WHOIS Lookup*\n\nSend a domain name:\n`example.com`",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif data == "mode_tguser":
        user_mode[uid] = "tguser"
        await query.edit_message_text(
            "👤 *Telegram User Info*\n\nForward any message from the user you want to investigate, or send their @username:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

    elif data == "mode_leak":
        user_mode[uid] = "leak"
        await query.edit_message_text(
            "💾 *Leaked Data Search*\n\nSend an email address to check against known breach databases:",
            parse_mode="Markdown", reply_markup=back_keyboard()
        )

# ──────────────────────────────────────────────
# MESSAGE HANDLER — ROUTES BY MODE
# ──────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    mode = user_mode.get(uid)

    if not mode:
        await update.message.reply_text(
            "Please choose a tool first:",
            reply_markup=main_menu_keyboard()
        )
        return

    msg = update.message

    if mode == "phone":
        await handle_phone(msg)
    elif mode == "email":
        await handle_email(msg)
    elif mode == "whois":
        await handle_whois(msg)
    elif mode == "tguser":
        await handle_tguser(msg)
    elif mode == "leak":
        await handle_leak(msg)

# ──────────────────────────────────────────────
# TOOL: PHONE LOOKUP
# ──────────────────────────────────────────────

async def handle_phone(msg):
    text = msg.text.strip()
    await msg.reply_text("🔍 Looking up phone number...")

    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone

        phone = phonenumbers.parse(text)
        if not phonenumbers.is_valid_number(phone):
            await msg.reply_text("❌ Invalid phone number. Use international format: `+1234567890`", parse_mode="Markdown", reply_markup=back_keyboard())
            return

        country   = geocoder.description_for_number(phone, "en")
        carrier_  = carrier.name_for_number(phone, "en")
        timezones = timezone.time_zones_for_number(phone)
        fmt_intl  = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        fmt_e164  = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
        num_type  = phonenumbers.number_type(phone)

        type_map = {
            0: "Fixed Line", 1: "Mobile", 2: "Fixed/Mobile",
            3: "Toll Free", 4: "Premium Rate", 6: "VOIP",
            7: "Personal", 99: "Unknown"
        }
        line_type = type_map.get(num_type, "Unknown")

        # Geo IP enrichment via free API
        geo_info = ""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"https://restcountries.com/v3.1/callingcode/{phone.country_code}")
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        capital = data[0].get("capital", ["N/A"])[0]
                        region  = data[0].get("region", "N/A")
                        geo_info = f"\n🌍 *Region:* {region}\n🏛 *Capital:* {capital}"
        except Exception:
            pass

        result = (
            f"📱 *Phone Number Report*\n"
            f"{'─'*30}\n"
            f"📞 *Number:* `{fmt_intl}`\n"
            f"🔢 *E164:* `{fmt_e164}`\n"
            f"🌐 *Country:* {country or 'Unknown'}{geo_info}\n"
            f"📡 *Carrier:* {carrier_ or 'Unknown'}\n"
            f"📶 *Line Type:* {line_type}\n"
            f"🕐 *Timezones:* {', '.join(timezones) or 'Unknown'}\n"
            f"✅ *Valid:* {'Yes' if phonenumbers.is_valid_number(phone) else 'No'}\n"
            f"📍 *Possible:* {'Yes' if phonenumbers.is_possible_number(phone) else 'No'}\n\n"
            f"🔗 *Check further:*\n"
            f"• [OSINT Rocks](https://osint.rocks/)\n"
            f"• [TrueCaller Bot](https://t.me/TrueCaller_Z_Bot)\n"
            f"• [GetContact Bot](https://t.me/getcontact_real_bot)"
        )
        await msg.reply_text(result, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}\n\nMake sure to use international format: `+1234567890`", parse_mode="Markdown", reply_markup=back_keyboard())

# ──────────────────────────────────────────────
# TOOL: EMAIL / USERNAME SEARCH
# ──────────────────────────────────────────────

async def handle_email(msg):
    text = msg.text.strip()
    await msg.reply_text("🔍 Searching...")

    is_email = "@" in text and "." in text.split("@")[-1]

    if is_email:
        domain = text.split("@")[-1]
        result = (
            f"📧 *Email Investigation*\n"
            f"{'─'*30}\n"
            f"📮 *Email:* `{text}`\n"
            f"🌐 *Domain:* `{domain}`\n\n"
            f"🔗 *Check these resources:*\n"
            f"• [HaveIBeenPwned](https://haveibeenpwned.com/account/{text}) — Breach check\n"
            f"• [LeakCheck Bot](https://web.telegram.org/k/#@LeakCheckBot) — Telegram breach bot\n"
            f"• [Hunter.io](https://hunter.io/email-verifier/{text}) — Email verify\n"
            f"• [Epieos](https://epieos.com/?q={text}&t=email) — Google/Gravatar lookup\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={text}) — Leaked DB search\n"
            f"• [EmailRep](https://emailrep.io/{text}) — Reputation check\n\n"
            f"💡 *Tip:* Also try the [All In One Leaks Bot](https://t.me/AllInOneLeaksBOT)"
        )
    else:
        # Username search
        username = text.lstrip("@")
        result = (
            f"👤 *Username Investigation*\n"
            f"{'─'*30}\n"
            f"🔎 *Username:* `{username}`\n\n"
            f"🔗 *Check these resources:*\n"
            f"• [Maigret OSINT Bot](https://t.me/maigret_osint_bot) — 500+ sites\n"
            f"• [Sherlock (Web)](https://sherlock-project.github.io/) — Username hunt\n"
            f"• [WhatsMyName](https://whatsmyname.app/?q={username}) — Cross-platform\n"
            f"• [Namechk](https://namechk.com/{username}) — Social check\n"
            f"• [UserSearch](https://usersearch.org/results_normal.php?URL_username={username})\n"
            f"• [Telegram: @{username}](https://t.me/{username}) — Direct Telegram link\n\n"
            f"💡 *Tip:* Use [Leak Check Bot](https://web.telegram.org/k/#@LeakCheckBot) for breach checks"
        )

    await msg.reply_text(result, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

# ──────────────────────────────────────────────
# TOOL: WHOIS
# ──────────────────────────────────────────────

async def handle_whois(msg):
    domain = msg.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    await msg.reply_text(f"🔍 Running WHOIS on `{domain}`...", parse_mode="Markdown")

    try:
        loop = asyncio.get_event_loop()
        w = await loop.run_in_executor(None, whois.whois, domain)

        def fmt(val):
            if val is None:
                return "N/A"
            if isinstance(val, list):
                val = val[0]
            if isinstance(val, datetime):
                return val.strftime("%Y-%m-%d %H:%M UTC")
            return str(val)

        # DNS resolution
        try:
            ip = socket.gethostbyname(domain)
        except Exception:
            ip = "N/A"

        registrar   = fmt(w.registrar)
        created     = fmt(w.creation_date)
        expires     = fmt(w.expiration_date)
        updated     = fmt(w.updated_date)
        name_servers= ", ".join(w.name_servers[:3]) if w.name_servers else "N/A"
        country     = fmt(w.country)
        org         = fmt(getattr(w, "org", None) or getattr(w, "organization", None))
        status      = fmt(w.status) if isinstance(w.status, str) else (w.status[0] if w.status else "N/A")

        result = (
            f"🌐 *WHOIS Report: {domain}*\n"
            f"{'─'*30}\n"
            f"🏢 *Registrar:* {registrar}\n"
            f"📅 *Created:* {created}\n"
            f"⏰ *Expires:* {expires}\n"
            f"🔄 *Updated:* {updated}\n"
            f"🖥 *IP Address:* `{ip}`\n"
            f"🌍 *Country:* {country}\n"
            f"🏛 *Org:* {org}\n"
            f"📡 *Name Servers:* {name_servers}\n"
            f"🔒 *Status:* {status[:60] if len(status) > 60 else status}\n\n"
            f"🔗 *Further investigation:*\n"
            f"• [ViewDNS](https://viewdns.info/whois/?domain={domain})\n"
            f"• [SecurityTrails](https://securitytrails.com/domain/{domain}/dns)\n"
            f"• [VirusTotal](https://www.virustotal.com/gui/domain/{domain})\n"
            f"• [Shodan](https://www.shodan.io/search?query={domain})"
        )
        await msg.reply_text(result, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

    except Exception as e:
        await msg.reply_text(f"❌ WHOIS failed: {e}", reply_markup=back_keyboard())

# ──────────────────────────────────────────────
# TOOL: TELEGRAM USER INFO
# ──────────────────────────────────────────────

async def handle_tguser(msg):
    # Check if forwarded message
    if msg.forward_from:
        user = msg.forward_from
        uid       = user.id
        first     = user.first_name or ""
        last      = user.last_name or ""
        username  = f"@{user.username}" if user.username else "N/A"
        is_bot    = "✅ Yes" if user.is_bot else "❌ No"
        lang      = user.language_code or "N/A"
        premium   = "✅ Yes" if getattr(user, "is_premium", False) else "❌ No"

        # Estimate account age from ID (rough heuristic)
        age_hint = estimate_account_age(uid)

        result = (
            f"👤 *Telegram User Info*\n"
            f"{'─'*30}\n"
            f"🆔 *User ID:* `{uid}`\n"
            f"👤 *Name:* {first} {last}\n"
            f"📛 *Username:* {username}\n"
            f"🤖 *Is Bot:* {is_bot}\n"
            f"🌐 *Language:* {lang}\n"
            f"⭐ *Premium:* {premium}\n"
            f"📅 *Account Age Estimate:* {age_hint}\n\n"
            f"🔗 *Further investigation:*\n"
            f"• [Creation Date Bot](https://t.me/creationdatebot) — Exact creation date\n"
            f"• [UserInfo Bot](https://t.me/userinfobot) — Forward message there too\n"
            f"• [TelegramDB](https://www.telegramdb.org/search) — Group membership\n"
            f"• [TGScan Robot](https://t.me/tgscanrobot) — Find user's groups"
        )
        if username != "N/A":
            uname = username.lstrip("@")
            result += f"\n• [Profile](https://t.me/{uname}) — Direct link"

    elif msg.text and msg.text.startswith("@"):
        username = msg.text.strip().lstrip("@")
        result = (
            f"👤 *Telegram Username Lookup*\n"
            f"{'─'*30}\n"
            f"📛 *Username:* @{username}\n"
            f"🔗 *Profile:* t.me/{username}\n\n"
            f"🔗 *Investigate further:*\n"
            f"• [Direct Profile](https://t.me/{username})\n"
            f"• [Web View K](https://web.telegram.org/k/#@{username})\n"
            f"• [Web View Z](https://web.telegram.org/z/#@{username})\n"
            f"• [Username→ID Bot](https://t.me/username_to_id_bot)\n"
            f"• [Creation Date Bot](https://t.me/creationdatebot)\n"
            f"• [TelegramDB Search](https://www.telegramdb.org/search)\n"
            f"• [SangMata Bot](https://t.me/SangMata_beta_bot) — Name history"
        )
    else:
        result = (
            "ℹ️ *How to use Telegram User Info:*\n\n"
            "1️⃣ *Forward* a message from the target user to this chat\n"
            "2️⃣ Or send their `@username`\n\n"
            "⚠️ Note: Users with 'Forward Privacy' enabled will hide their info from forwards."
        )

    await msg.reply_text(result, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

def estimate_account_age(user_id: int) -> str:
    """Rough estimate based on Telegram ID ranges."""
    ranges = [
        (100000000,   "~2013-2014 (Very old)"),
        (500000000,   "~2014-2016 (Old)"),
        (1000000000,  "~2016-2018"),
        (2000000000,  "~2018-2019"),
        (4000000000,  "~2019-2020"),
        (6000000000,  "~2020-2021"),
        (8000000000,  "~2021-2022"),
        (10000000000, "~2022-2023"),
        (float("inf"),"~2023-2024 (Recent)"),
    ]
    for threshold, label in ranges:
        if user_id < threshold:
            return label
    return "Unknown"

# ──────────────────────────────────────────────
# TOOL: LEAKED DATA SEARCH
# ──────────────────────────────────────────────

async def handle_leak(msg):
    query = msg.text.strip()
    await msg.reply_text("🔍 Checking breach databases...")

    is_email = "@" in query

    # Try HIBP API (free, no key needed for basic check)
    hibp_result = ""
    if is_email:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"https://haveibeenpwned.com/api/v3/breachedaccount/{query}",
                    headers={
                        "User-Agent": "OSINT-Bot",
                        "hibp-api-key": os.getenv("HIBP_API_KEY", "")
                    }
                )
                if r.status_code == 200:
                    breaches = r.json()
                    names = [b["Name"] for b in breaches[:10]]
                    hibp_result = f"\n\n🔴 *Found in {len(breaches)} breaches:*\n" + "\n".join(f"• {n}" for n in names)
                    if len(breaches) > 10:
                        hibp_result += f"\n• ...and {len(breaches)-10} more"
                elif r.status_code == 404:
                    hibp_result = "\n\n✅ *Not found in HIBP database*"
                elif r.status_code == 401:
                    hibp_result = "\n\n⚠️ HIBP API key required for detailed results"
        except Exception as e:
            hibp_result = f"\n\n⚠️ HIBP check skipped: {e}"

    result = (
        f"💾 *Leaked Data Search*\n"
        f"{'─'*30}\n"
        f"🔎 *Query:* `{query}`\n"
        f"{'📧 Type: Email' if is_email else '👤 Type: Username'}"
        f"{hibp_result}\n\n"
        f"🔗 *Manual checks (click to open):*\n"
    )

    if is_email:
        result += (
            f"• [HaveIBeenPwned](https://haveibeenpwned.com/account/{query})\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={query})\n"
            f"• [LeakCheck](https://leakcheck.io/search?query={query})\n"
            f"• [BreachDirectory](https://breachdirectory.org/)\n"
            f"• [Snusbase](https://snusbase.com/)\n"
            f"• [IntelX](https://intelx.io/?s={query})\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [LeakCheck Bot](https://web.telegram.org/k/#@LeakCheckBot)\n"
            f"• [All In One Leaks](https://t.me/AllInOneLeaksBOT)\n"
            f"• [Email Leaks Bot](https://t.me/EmailLeaks_bot)\n"
            f"• [Data Leaks Bot](https://t.me/dataLeaks_bot)"
        )
    else:
        result += (
            f"• [IntelX](https://intelx.io/?s={query})\n"
            f"• [BreachDirectory](https://breachdirectory.org/)\n"
            f"• [Dehashed](https://www.dehashed.com/search?query={query})\n\n"
            f"🤖 *Telegram Bots:*\n"
            f"• [LeakCheck Bot](https://web.telegram.org/k/#@LeakCheckBot)\n"
            f"• [All In One Leaks](https://t.me/AllInOneLeaksBOT)\n"
            f"• [SOVA App Bot](https://t.me/sovaappbot)"
        )

    await msg.reply_text(result, parse_mode="Markdown", reply_markup=back_keyboard(), disable_web_page_preview=True)

# ──────────────────────────────────────────────
# FORWARDED MESSAGE HANDLER
# ──────────────────────────────────────────────

async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if user_mode.get(uid) == "tguser":
        await handle_tguser(update.message)
    else:
        # Auto-detect even if no mode set
        user_mode[uid] = "tguser"
        await handle_tguser(update.message)

# ──────────────────────────────────────────────
# ERROR HANDLER
# ──────────────────────────────────────────────

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.FORWARDED, forward_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    print("🤖 OSINT Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()