import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from imdb import IMDb

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)

# IMDb instance
ia = IMDb()

# Flask app for health check
app = Flask(__name__)

# Dictionary to store filters and admins
filters = {}
admins = set()
source_channel_id = os.getenv("SOURCE_CHANNEL_ID")
request_channel_id = os.getenv("REQUEST_CHANNEL_ID")
PORT = int(os.environ.get("PORT", 5000))

# Ensure bot admins are set
default_admin = int(os.getenv("OWNER_ID", 0))
admins.add(default_admin)

# Health check endpoint
@app.route('/')
def health_check():
    return "Bot is running!", 200

# Add admin command
def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != default_admin:
        update.message.reply_text("Only the bot owner can add admins.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("Usage: /addadmin <user_id>")
        return
    new_admin_id = int(context.args[0])
    admins.add(new_admin_id)
    update.message.reply_text(f"User {new_admin_id} added as an admin.")

# Remove admin command
def remove_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != default_admin:
        update.message.reply_text("Only the bot owner can remove admins.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    admin_id = int(context.args[0])
    if admin_id in admins:
        admins.remove(admin_id)
        update.message.reply_text(f"User {admin_id} removed as an admin.")
    else:
        update.message.reply_text(f"User {admin_id} is not an admin.")

# Custom welcome message (admin only)
def set_welcome_message(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in admins:
        update.message.reply_text("Only admins can set the welcome message.")
        return
    welcome_message = ' '.join(context.args)
    os.environ['WELCOME_MESSAGE'] = welcome_message
    update.message.reply_text("Welcome message updated.")

# Handle new users and send the custom welcome message
def welcome(update: Update, context: CallbackContext) -> None:
    welcome_message = os.getenv('WELCOME_MESSAGE', "Welcome to the channel!")
    update.message.reply_text(welcome_message)

# Request movie feature
def request_movie(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        update.message.reply_text("Usage: /request <movie_name>")
        return
    movie_name = ' '.join(context.args)
    context.bot.send_message(request_channel_id, f"New movie request: {movie_name}")
    update.message.reply_text(f"Your request for '{movie_name}' has been sent.")

# IMDb search
def imdb_search(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        update.message.reply_text("Usage: /imdb <movie_name>")
        return
    movie_name = ' '.join(context.args)
    movies = ia.search_movie(movie_name)
    if movies:
        movie = movies[0]
        ia.update(movie)
        movie_info = f"Title: {movie['title']}\nYear: {movie['year']}\nRating: {movie.get('rating', 'N/A')}\nPlot: {movie.get('plot outline', 'N/A')}"
        update.message.reply_text(movie_info)
    else:
        update.message.reply_text("Movie not found!")

# Add a filter (admin only)
def add_filter(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in admins:
        update.message.reply_text("Only admins can add filters.")
        return
    if len(context.args) < 2:
        update.message.reply_text("Usage: /addfilter <keyword> <reply>")
        return
    keyword = context.args[0].lower()
    reply = ' '.join(context.args[1:])
    filters[keyword] = reply
    update.message.reply_text(f"Filter added: '{keyword}' will trigger '{reply}'.")

# Other bot functions remain unchanged...

# Main function to run the bot
def main():
    token = os.getenv("TOKEN")
    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addfilter", add_filter))
    dp.add_handler(CommandHandler("removefilter", remove_filter))
    dp.add_handler(CommandHandler("listfilters", list_filters))
    dp.add_handler(CommandHandler("clearfilters", clear_filters))
    dp.add_handler(CommandHandler("imdb", imdb_search))
    dp.add_handler(CommandHandler("request", request_movie))
    dp.add_handler(CommandHandler("addadmin", add_admin))
    dp.add_handler(CommandHandler("removeadmin", remove_admin))
    dp.add_handler(CommandHandler("setwelcome", set_welcome_message))

    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, filter_from_channel))

    updater.start_polling()
    
    # For health checks (Heroku)
    app.run(host="0.0.0.0", port=PORT)

    updater.idle()

if __name__ == '__main__':
    main()
