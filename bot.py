import os
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

DATA_FILE = "bot_data.json"

# ===== GLOBAL STATE =====
DEFAULT_BOT_DATA = {
    "links": [],
    "current_link_index": 0,
    "rotation_interval": 300,  # default 5 minutes
    "admins": [],
    "users": []
}

bot_data = DEFAULT_BOT_DATA.copy()

# ===== STORAGE =====
def load_data():
    global bot_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                loaded_data = json.load(f)
                # Validate required keys
                required_keys = ["links", "current_link_index", "rotation_interval", "admins", "users"]
                if all(key in loaded_data for key in required_keys):
                    bot_data = loaded_data
                else:
                    print("Warning: Data file missing required keys, using default values")
    except json.JSONDecodeError:
        print("Error: Invalid JSON in data file, using default values")
    except Exception as e:
        print(f"Error loading data: {str(e)}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(bot_data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {str(e)}")

# ===== ADMIN CHECK =====
def is_admin(user_id):
    return str(user_id) in map(str, bot_data["admins"])

# ===== AUTO LINK ROTATION =====
async def auto_rotate():
    while True:
        try:
            await asyncio.sleep(bot_data["rotation_interval"])
            if bot_data["links"]:
                bot_data["current_link_index"] = (bot_data["current_link_index"] + 1) % len(bot_data["links"])
                save_data()
        except Exception as e:
            print(f"Error in auto rotation: {str(e)}")
            await asyncio.sleep(60)  # Wait before retrying

# ===== GET CURRENT LINK =====
def current_link():
    if not bot_data["links"]:
        return "No link set."
    if bot_data["current_link_index"] >= len(bot_data["links"]):
        bot_data["current_link_index"] = 0
        save_data()
    return bot_data["links"][bot_data["current_link_index"]]

# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        if user_id not in bot_data["users"]:
            bot_data["users"].append(user_id)
            save_data()
        button = InlineKeyboardButton("📥 Get Latest Link", callback_data="get_link")
        reply_markup = InlineKeyboardMarkup([[button]])
        await update.message.reply_text(
            "Welcome! Click below to get the latest channel link.",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error in start command: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        if query.data == "get_link":
            await query.edit_message_text(f"Here is your latest link:\n{current_link()}")
    except Exception as e:
        print(f"Error in button handler: {str(e)}")

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a link.")
        return

    link = " ".join(context.args)
    
    # Basic link validation
    if not link.startswith(('http://', 'https://', 't.me/')):
        await update.message.reply_text("Invalid link format. Please provide a valid URL or Telegram link.")
        return

    try:
        if link not in bot_data["links"]:
            bot_data["links"].append(link)
            save_data()
            await update.message.reply_text(f"Link added: {link}")
        else:
            await update.message.reply_text("Link already exists.")
    except Exception as e:
        print(f"Error adding link: {str(e)}")
        await update.message.reply_text("An error occurred while adding the link.")

async def removelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Please provide the link to remove.")
        return

    try:
        link = " ".join(context.args)
        if link in bot_data["links"]:
            bot_data["links"].remove(link)
            if bot_data["current_link_index"] >= len(bot_data["links"]):
                bot_data["current_link_index"] = 0
            save_data()
            await update.message.reply_text(f"Link removed: {link}")
        else:
            await update.message.reply_text("Link not found.")
    except Exception as e:
        print(f"Error removing link: {str(e)}")
        await update.message.reply_text("An error occurred while removing the link.")

async def listlinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    try:
        if not bot_data["links"]:
            await update.message.reply_text("No links found.")
            return
        text = "\n".join(f"{idx+1}. {link}" for idx, link in enumerate(bot_data["links"]))
        await update.message.reply_text(f"Links:\n{text}")
    except Exception as e:
        print(f"Error listing links: {str(e)}")
        await update.message.reply_text("An error occurred while listing the links.")

async def settimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Please provide timer in minutes (e.g., /settimer 10).")
        return

    try:
        minutes = int(context.args[0])
        if minutes <= 0:
            await update.message.reply_text("Please provide a positive number of minutes.")
            return
        if minutes > 1440:  # 24 hours max
            await update.message.reply_text("Timer cannot be set for more than 24 hours (1440 minutes).")
            return

        bot_data["rotation_interval"] = minutes * 60
        save_data()
        await update.message.reply_text(f"Rotation interval set to {minutes} minutes.")
    except ValueError:
        await update.message.reply_text("Invalid input. Please provide an integer value for minutes.")
    except Exception as e:
        print(f"Error setting timer: {str(e)}")
        await update.message.reply_text("An error occurred while setting the timer.")

async def currentlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    try:
        await update.message.reply_text(f"Current link: {current_link()}")
    except Exception as e:
        print(f"Error getting current link: {str(e)}")
        await update.message.reply_text("An error occurred while getting the current link.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    try:
        message = " ".join(context.args)
        count = 0
        failed = 0
        for user in bot_data["users"]:
            try:
                await context.bot.send_message(chat_id=user, text=message)
                count += 1
            except Exception:
                failed += 1
                continue
        await update.message.reply_text(f"Broadcast sent to {count} users. Failed: {failed}")
    except Exception as e:
        print(f"Error broadcasting message: {str(e)}")
        await update.message.reply_text("An error occurred while broadcasting the message.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_data["admins"] or str(update.effective_user.id) != bot_data["admins"][0]:
        await update.message.reply_text("Only owner can add admins.")
        return

    if not context.args:
        await update.message.reply_text("Please provide user ID to add as admin.")
        return

    try:
        user_id = context.args[0]
        if user_id not in bot_data["admins"]:
            bot_data["admins"].append(user_id)
            save_data()
            await update.message.reply_text(f"Admin added: {user_id}")
        else:
            await update.message.reply_text("User is already an admin.")
    except Exception as e:
        print(f"Error adding admin: {str(e)}")
        await update.message.reply_text("An error occurred while adding the admin.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_data["admins"] or str(update.effective_user.id) != bot_data["admins"][0]:
        await update.message.reply_text("Only owner can remove admins.")
        return

    if not context.args:
        await update.message.reply_text("Please provide user ID to remove from admins.")
        return

    try:
        user_id = context.args[0]
        if user_id in bot_data["admins"]:
            # Prevent removing the owner (first admin)
            if user_id == bot_data["admins"][0]:
                await update.message.reply_text("Cannot remove the owner.")
                return
            bot_data["admins"].remove(user_id)
            save_data()
            await update.message.reply_text(f"Admin removed: {user_id}")
        else:
            await update.message.reply_text("User is not an admin.")
    except Exception as e:
        print(f"Error removing admin: {str(e)}")
        await update.message.reply_text("An error occurred while removing the admin.")

async def adminslist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_data["admins"] or str(update.effective_user.id) != bot_data["admins"][0]:
        await update.message.reply_text("Only owner can view admins.")
        return

    try:
        if not bot_data["admins"]:
            await update.message.reply_text("No admins set.")
            return
        text = "\n".join(f"{idx+1}. {admin}" for idx, admin in enumerate(bot_data["admins"]))
        await update.message.reply_text(f"Admins:\n{text}")
    except Exception as e:
        print(f"Error listing admins: {str(e)}")
        await update.message.reply_text("An error occurred while listing the admins.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        help_text = """Commands:
/start - Get started
/addlink LINK - Add a new channel link
/removelink LINK - Remove a channel link
/listlinks - List all channel links
/settimer MINUTES - Set link rotation timer (in minutes)
/currentlink - Show current link
/broadcast MESSAGE - Send message to all users
/addadmin USERID - Add admin (owner only)
/removeadmin USERID - Remove admin (owner only)
/adminslist - List admins (owner only)
/help - Show this help message
"""
        await update.message.reply_text(help_text)
    except Exception as e:
        print(f"Error showing help: {str(e)}")
        await update.message.reply_text("An error occurred while showing the help message.")

async def main():
    try:
        # Load saved data
        load_data()

        # Initialize bot
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # Add command handlers
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

        # Start auto rotation task
        asyncio.create_task(auto_rotate())
        
        print("Bot is running...")
        await app.run_polling()

    except Exception as e:
        print(f"Critical error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
