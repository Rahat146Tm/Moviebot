import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from imdb import IMDb
from threading import Thread
from datetime import datetime
import time

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

# Custom welcome GIF for new users
WELCOME_GIF = "https://media.giphy.com/media/l4EoXfRgs6nIuCImk/giphy.gif"

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

# Dynamic main menu with buttons
def main_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Search IMDb", callback_data='search')],
        [InlineKeyboardButton("Request Movie", callback_data='request')],
        [InlineKeyboardButton("View Filters", callback_data='filters')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome to the Bot! Choose an option:', reply_markup=reply_markup)

# Callback handler for the main menu
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'search':
        query.edit_message_text(text="Type the movie name with /imdb <movie_name>.")
    elif query.data == 'request':
        query.edit_message_text(text="Request a movie by using /request <movie_name>.")
    elif query.data == 'filters':
        query.edit_message_text(text="Use /listfilters to see all current filters.")

# Welcome new users with a GIF
def welcome(update: Update, context: CallbackContext) -> None:
    welcome_message = os.getenv('WELCOME_MESSAGE', "Welcome to the channel!")
    context.bot.send_animation(chat_id=update.message.chat_id, animation=WELCOME_GIF, caption=welcome_message)

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
        movie_info = f"*Title*: {movie['title']}\n*Year*: {movie['year']}\n*Rating*: {movie.get('rating', 'N/A')}\n*Plot*: {movie.get('plot outline', 'N/A')}"
        update.message.reply_text(movie_info, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text("Movie not found!")

# Scheduled task to clear filters every 24 hours
def clear_old_filters():
    while True:
        time.sleep(86400)  # Wait for 24 hours
        filters.clear()
        logging.info("Cleared old filters")

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

# Main function to run the bot
def main():
    token = os.getenv("TOKEN")
    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", main_menu))
    dp.add_handler(CommandHandler("addfilter", add_filter))
    dp.add_handler(CommandHandler("removefilter", remove_filter))
    dp.add_handler(CommandHandler("listfilters", list_filters))
    dp.add_handler(CommandHandler("clearfilters", clear_filters))
    dp.add_handler(CommandHandler("imdb", imdb_search))
    dp.add_handler(CommandHandler("request", request_movie))
    dp.add_handler(CommandHandler("addadmin", add_admin))
    dp.add_handler(CommandHandler("removeadmin", remove_admin))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))

    dp.add_handler(CallbackQueryHandler(button))  # Handle inline button clicks

    # Start a thread for clearing old filters
    thread = Thread(target=clear_old_filters)
    thread.start()

    updater.start_polling()

    # For health checks (Heroku)
    app.run(host="0.0.0.0", port=PORT)

    updater.idle()

if __name__ == '__main__':
    main()
