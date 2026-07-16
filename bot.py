#!/usr/bin/env python3
"""
Telegram Promotions Bot
Publishes rotating promotions with media albums and admin contact buttons.
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, Update
from telegram.ext import Application, ContextTypes, CommandHandler
from telegram.error import TelegramError

from promotions_config import PROMOTIONS, PROMOTION_INTERVAL

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", 0))
STATE_FILE = "bot_state.json"

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class BotState:
    """Manages the bot state (message IDs and current promotion)."""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load state from JSON file."""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return {
            "current_promotion_index": 0,
            "last_album_message_id": None,
            "last_button_message_id": None,
            "last_published": None,
        }

    def save(self):
        """Save state to JSON file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.data, f, indent=2)
            logger.info("State saved successfully")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_current_promotion_index(self) -> int:
        """Get the current promotion index."""
        return self.data.get("current_promotion_index", 0)

    def set_current_promotion_index(self, index: int):
        """Set the current promotion index."""
        self.data["current_promotion_index"] = index

    def get_last_album_message_id(self) -> Optional[int]:
        """Get the ID of the last album message."""
        return self.data.get("last_album_message_id")

    def set_last_album_message_id(self, message_id: Optional[int]):
        """Set the ID of the last album message."""
        self.data["last_album_message_id"] = message_id

    def get_last_button_message_id(self) -> Optional[int]:
        """Get the ID of the last button message."""
        return self.data.get("last_button_message_id")

    def set_last_button_message_id(self, message_id: Optional[int]):
        """Set the ID of the last button message."""
        self.data["last_button_message_id"] = message_id

    def get_last_published(self) -> Optional[str]:
        """Get the timestamp of the last published promotion."""
        return self.data.get("last_published")

    def set_last_published(self, timestamp: str):
        """Set the timestamp of the last published promotion."""
        self.data["last_published"] = timestamp


def validate_configuration() -> bool:
    """Validate that all required configuration is set."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set")
        return False
    if not GROUP_ID or GROUP_ID == 0:
        logger.error("GROUP_ID environment variable not set or invalid")
        return False
    if not PROMOTIONS:
        logger.error("No promotions configured in promotions_config.py")
        return False
    return True


def get_media_input_objects(media_paths: List[str]) -> List:
    """
    Convert media file paths to Telegram InputMedia objects.
    Supports JPG, PNG, MP4, etc.
    """
    media_objects = []
    for path in media_paths:
        if not os.path.exists(path):
            logger.warning(f"Media file not found: {path}")
            continue

        # Determine media type from extension
        ext = Path(path).suffix.lower()
        try:
            # Use the file path directly (Telegram handles file reading)
            if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                media_objects.append(InputMediaPhoto(media=path))
            elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                media_objects.append(InputMediaVideo(media=path))
            else:
                logger.warning(f"Unsupported media format: {ext}")
        except Exception as e:
            logger.error(f"Failed to load media file {path}: {e}")

    return media_objects


async def delete_previous_messages(context: ContextTypes.DEFAULT_TYPE, state: BotState):
    """Delete the previous promotion's album and button messages."""
    album_msg_id = state.get_last_album_message_id()
    button_msg_id = state.get_last_button_message_id()

    deleted_count = 0

    if album_msg_id:
        try:
            # Album messages need special handling - delete each message in the group
            await context.bot.delete_message(chat_id=GROUP_ID, message_id=album_msg_id)
            logger.info(f"Deleted album message: {album_msg_id}")
            deleted_count += 1
        except TelegramError as e:
            logger.warning(f"Could not delete album message {album_msg_id}: {e}")

    if button_msg_id:
        try:
            await context.bot.delete_message(chat_id=GROUP_ID, message_id=button_msg_id)
            logger.info(f"Deleted button message: {button_msg_id}")
            deleted_count += 1
        except TelegramError as e:
            logger.warning(f"Could not delete button message {button_msg_id}: {e}")

    return deleted_count > 0


async def publish_promotion(context: ContextTypes.DEFAULT_TYPE):
    """Publish the current promotion."""
    state = BotState()
    
    # Delete previous messages
    await delete_previous_messages(context, state)

    # Get current promotion
    promotion_index = state.get_current_promotion_index()
    promotion = PROMOTIONS[promotion_index]

    logger.info(f"Publishing promotion {promotion['id']} ({promotion_index + 1}/{len(PROMOTIONS)})")

    album_message = None
    button_message = None

    try:
        # Publish media album if media exists
        if promotion["media"]:
            media_objects = get_media_input_objects(promotion["media"])
            if media_objects:
                # Set caption only for the first media item
                media_objects[0].caption = promotion["caption"]
                media_objects[0].parse_mode = "Markdown"

                album_message = await context.bot.send_media_group(
                    chat_id=GROUP_ID,
                    media=media_objects,
                )
                logger.info(f"Album published with {len(album_message)} messages")
                state.set_last_album_message_id(album_message[0].message_id)
            else:
                # No valid media files, publish caption as text
                text_message = await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=promotion["caption"],
                    parse_mode="Markdown",
                )
                state.set_last_album_message_id(text_message.message_id)
                logger.info("Published promotion as text (no valid media files)")
        else:
            # No media configured, publish caption as text
            text_message = await context.bot.send_message(
                chat_id=GROUP_ID,
                text=promotion["caption"],
                parse_mode="Markdown",
            )
            state.set_last_album_message_id(text_message.message_id)
            logger.info("Published promotion as text (no media configured)")

        # Publish button message with admin contact
        admin_username = promotion["admin_username"]
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👤 Hablar con el administrador", url=f"https://t.me/{admin_username}")]]
        )
        button_message = await context.bot.send_message(
            chat_id=GROUP_ID,
            text="👇 Para más información:",
            reply_markup=keyboard,
        )
        logger.info(f"Button message published: {button_message.message_id}")
        state.set_last_button_message_id(button_message.message_id)

        # Pin button message silently
        if button_message:
            try:
                await context.bot.pin_chat_message(
                    chat_id=GROUP_ID,
                    message_id=button_message.message_id,
                    disable_notification=True,
                )
                logger.info(f"Pinned button message: {button_message.message_id}")
            except TelegramError as e:
                logger.warning(f"Could not pin message: {e}")

        # Update state for next promotion
        next_index = (promotion_index + 1) % len(PROMOTIONS)
        state.set_current_promotion_index(next_index)
        state.set_last_published(datetime.now().isoformat())
        state.save()

        logger.info(f"Promotion published successfully. Next promotion index: {next_index}")

    except TelegramError as e:
        logger.error(f"Failed to publish promotion: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while publishing promotion: {e}")


async def schedule_promotions(context: ContextTypes.DEFAULT_TYPE):
    """Schedule periodic promotion publishing."""
    # Remove any existing jobs
    removed = context.job_queue.get_jobs_by_name("promotion_job")
    for job in removed:
        job.schedule_removal()

    # Schedule first promotion after 1 minute, then every PROMOTION_INTERVAL seconds
    context.job_queue.run_once(
        publish_promotion,
        when=60,
        name="promotion_job_initial",
    )
    logger.info("Initial promotion scheduled in 60 seconds")

    context.job_queue.run_repeating(
        publish_promotion,
        interval=PROMOTION_INTERVAL,
        first=PROMOTION_INTERVAL + 60,
        name="promotion_job",
    )
    logger.info(f"Promotions scheduled to repeat every {PROMOTION_INTERVAL} seconds ({PROMOTION_INTERVAL / 3600} hours)")


async def post_init(application: Application):
    """Called after the application is initialized."""
    logger.info("Bot started. Scheduling promotions...")
    await schedule_promotions(application)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    # Reply to the user confirming the bot is running
    if update.message:
        await update.message.reply_text(
            "✅ EC Promociones Bot está funcionando correctamente."
        )


def main():
    """Main function to start the bot."""
    # Validate configuration
    if not validate_configuration():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    logger.info("Starting Telegram Promotions Bot...")
    logger.info(f"Target group ID: {GROUP_ID}")
    logger.info(f"Number of promotions: {len(PROMOTIONS)}")
    logger.info(f"Promotion interval: {PROMOTION_INTERVAL} seconds ({PROMOTION_INTERVAL / 3600} hours)")

    # Create the Application using the modern API (compatible with v21.x)
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Register /start command handler
    application.add_handler(CommandHandler("start", start))

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main()
