import os import asyncio import json from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

===== CONFIG =====

BOT_TOKEN = os.environ.get("BOT_TOKEN") DATA_FILE = "bot_data.json"

===== GLOBAL STATE =====

bot_data = { "links": [], "current_link_index": 0, "rotation_interval": 300,  # default 5 minutes "admins": [], "users": [] }

===== STORAGE =====

def load_data(): global bot_data if os.path.exists(DATA_FILE): with open(DATA_FILE, "r") as f: bot_data = json.load(f)

def save_data(): with open(DATA_FILE, "w") as f: json.dump(bot_data, f)

===== ADMIN CHECK =====

def is_admin(user_id): return str(user_id) in bot_data["admins"]

===== AUTO LINK ROTATION =====

async def auto_rotate(): while True: await asyncio.sleep(bot_data["rotation_interval"]) if bot_data["links"]: bot_data["current_link_index"] = (bot_data["current_link_index"] + 1) % len(bot_data["links"]) save_data()

===== GET CURRENT LINK =====

def current_link(): if not bot_data["links"]: return "No link set." return bot_data["links"][bot_data["current_link_index"]]

===== COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) if user_id not in bot_data["users"]: bot_data["users"].append(user_id) save_data()

button = InlineKeyboardButton("📥 Get Latest Link", callback_data="get_link")
reply_markup = InlineKeyboardMarkup([[button]])
await update.message.reply_text("Welcome! Click below to get the latest channel link.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() if query.data == "get_link": await query.edit_message_text(f"Here is your link:\n{current_link()}")

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return link = " ".join(context.args) if link: bot_data["links"].append(link) save_data() await update.message.reply_text(f"Link added: {link}") else: await update.message.reply_text("Usage: /addlink LINK")

async def removelink(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return link = " ".join(context.args) if link in bot_data["links"]: bot_data["links"].remove(link) save_data() await update.message.reply_text("Link removed.") else: await update.message.reply_text("Link not found.")

async def listlinks(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return if not bot_data["links"]: await update.message.reply_text("No links available.") else: links_text = "\n".join(bot_data["links"]) await update.message.reply_text(f"Current Links:\n{links_text}")

async def settimer(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return try: minutes = int(context.args[0]) if minutes not in [5, 10, 20]: raise ValueError bot_data["rotation_interval"] = minutes * 60 save_data() await update.message.reply_text(f"Timer set to {minutes} minutes.") except: await update.message.reply_text("Usage: /settimer 5|10|20")

async def currentlink(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return await update.message.reply_text(f"Current active link:\n{current_link()}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): await update.message.reply_text("You are not authorized.") return message = " ".join(context.args) if not message: await update.message.reply_text("Usage: /broadcast Your message here.") return success = 0 for user_id in bot_data["users"]: try: await context.bot.send_message(chat_id=user_id, text=message) success += 1 except: continue await update.message.reply_text(f"Broadcast sent to {success} users.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE): if str(update.effective_user.id) != bot_data["admins"][0]: await update.message.reply_text("Only owner can add admins.") return user_id = context.args[0] if user_id not in bot_data["admins"]: bot_data["admins"].append(user_id) save_data() await update.message.reply_text(f"Admin added: {user_id}") else: await update.message.reply_text("User is already an admin.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE): if str(update.effective_user.id) != bot_data["admins"][0]: await update.message.reply_text("Only owner can remove admins.") return user_id = context.args[0] if user_id in bot_data["admins"] and user_id != bot_data["admins"][0]: bot_data["admins"].remove(user_id) save_data() await update.message.reply_text(f"Admin removed: {user_id}") else: await update.message.reply_text("Cannot remove owner or invalid admin.")

async def adminslist(update: Update, context: ContextTypes.DEFAULT_TYPE): if str(update.effective_user.id) != bot_data["admins"][0]: await update.message.reply_text("Only owner can view admins.") return await update.message.reply_text("Admins:\n" + "\n".join(bot_data["admins"]))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(""" Commands: /start - Get started /addlink LINK /removelink LINK /listlinks /settimer 5|10|20 /currentlink /broadcast MESSAGE /addadmin USER_ID /removeadmin USER_ID /adminslist /help """)

===== MAIN BOT =====

async def main(): load_data() app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

app.add_handler(CommandHandler("addlink", addlink))
app.add_handler(CommandHandler("removelink", removelink))
app.add_handler(CommandHandler("listlinks", listlinks))
app.add_handler(CommandHandler("settimer", settimer))
app.add_handler(CommandHandler("currentlink", currentlink))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("addadmin", addadmin))
app.add_handler(CommandHandler("removeadmin", removeadmin))
app.add_handler(CommandHandler("adminslist", adminslist))
app.add_handler(CommandHandler("help", help_command))

asyncio.create_task(auto_rotate())
print("Bot is running...")
await app.run_polling()

if name == "main": asyncio.run(main())

