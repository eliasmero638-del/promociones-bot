#!/usr/bin/env python3
"""
Telegram Promotions Bot with Admin Panel
Publishes rotating promotions with media albums and admin contact buttons.
Features admin panel for managing promotions.
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, Update
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, filters
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", 0))
ADMIN_USER_ID = 8710301236
PROMOTIONS_FILE = "promotions.json"
STATE_FILE = "bot_state.json"
PROMOTION_INTERVAL = 7200  # 2 hours

# Conversation states
ADD_PHOTO, ADD_CAPTION, ADD_USERNAME, EDIT_SELECT, EDIT_CAPTION, EDIT_MEDIA, EDIT_USERNAME, DELETE_SELECT, INTERVAL_INPUT = range(9)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class PromotionsManager:
    """Manages promotions stored in JSON file."""

    def __init__(self, file_path: str = PROMOTIONS_FILE):
        self.file_path = file_path
        self.data = self._load()

    def _load(self) -> dict:
        """Load promotions from JSON file."""
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load promotions file: {e}")
        return {"promotions": []}

    def save(self):
        """Save promotions to JSON file."""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
            logger.info("Promotions saved successfully")
        except Exception as e:
            logger.error(f"Failed to save promotions: {e}")

    def get_all(self) -> List[Dict]:
        """Get all promotions."""
        return self.data.get("promotions", [])

    def get_by_id(self, promo_id: str) -> Optional[Dict]:
        """Get promotion by ID."""
        for promo in self.get_all():
            if promo.get("id") == promo_id:
                return promo
        return None

    def add(self, promotion: Dict):
        """Add a new promotion."""
        self.data["promotions"].append(promotion)
        self.save()

    def update(self, promo_id: str, promotion: Dict):
        """Update an existing promotion."""
        for i, promo in enumerate(self.data["promotions"]):
            if promo.get("id") == promo_id:
                self.data["promotions"][i] = promotion
                self.save()
                return True
        return False

    def delete(self, promo_id: str) -> bool:
        """Delete a promotion by ID."""
        for i, promo in enumerate(self.data["promotions"]):
            if promo.get("id") == promo_id:
                self.data["promotions"].pop(i)
                self.save()
                return True
        return False


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
            "promotion_interval": PROMOTION_INTERVAL,
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
        return self.data.get("current_promotion_index", 0)

    def set_current_promotion_index(self, index: int):
        self.data["current_promotion_index"] = index

    def get_last_album_message_id(self) -> Optional[int]:
        return self.data.get("last_album_message_id")

    def set_last_album_message_id(self, message_id: Optional[int]):
        self.data["last_album_message_id"] = message_id

    def get_last_button_message_id(self) -> Optional[int]:
        return self.data.get("last_button_message_id")

    def set_last_button_message_id(self, message_id: Optional[int]):
        self.data["last_button_message_id"] = message_id

    def get_last_published(self) -> Optional[str]:
        return self.data.get("last_published")

    def set_last_published(self, timestamp: str):
        self.data["last_published"] = timestamp

    def get_promotion_interval(self) -> int:
        return self.data.get("promotion_interval", PROMOTION_INTERVAL)

    def set_promotion_interval(self, interval: int):
        self.data["promotion_interval"] = interval


def validate_configuration() -> bool:
    """Validate that all required configuration is set."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set")
        return False
    if not GROUP_ID or GROUP_ID == 0:
        logger.error("GROUP_ID environment variable not set or invalid")
        return False
    return True


def get_media_input_objects(media_paths: List[str]) -> List:
    """Convert media file paths to Telegram InputMedia objects."""
    media_objects = []
    for path in media_paths:
        if not os.path.exists(path):
            logger.warning(f"Media file not found: {path}")
            continue

        ext = Path(path).suffix.lower()
        try:
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
    """Publish the current promotion from promotions.json."""
    state = BotState()
    promotions_manager = PromotionsManager()
    promotions = promotions_manager.get_all()

    if not promotions:
        logger.warning("No promotions available to publish")
        return

    await delete_previous_messages(context, state)

    promotion_index = state.get_current_promotion_index()
    if promotion_index >= len(promotions):
        promotion_index = 0
    
    promotion = promotions[promotion_index]

    logger.info(f"Publishing promotion {promotion['id']} ({promotion_index + 1}/{len(promotions)})")

    album_message = None
    button_message = None

    try:
        if promotion.get("media"):
            media_objects = get_media_input_objects(promotion["media"])
            if media_objects:
                media_objects[0].caption = promotion.get("caption", "")
                media_objects[0].parse_mode = "Markdown"

                album_message = await context.bot.send_media_group(
                    chat_id=GROUP_ID,
                    media=media_objects,
                )
                logger.info(f"Album published with {len(album_message)} messages")
                state.set_last_album_message_id(album_message[0].message_id)
            else:
                text_message = await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=promotion.get("caption", ""),
                    parse_mode="Markdown",
                )
                state.set_last_album_message_id(text_message.message_id)
                logger.info("Published promotion as text (no valid media files)")
        else:
            text_message = await context.bot.send_message(
                chat_id=GROUP_ID,
                text=promotion.get("caption", ""),
                parse_mode="Markdown",
            )
            state.set_last_album_message_id(text_message.message_id)
            logger.info("Published promotion as text (no media configured)")

        admin_username = promotion.get("admin_username", "el593rm")
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

        next_index = (promotion_index + 1) % len(promotions)
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
    if context.job_queue is None:
        logger.error("JobQueue is not available. Make sure python-telegram-bot[job-queue] is installed.")
        return
    
    removed = context.job_queue.get_jobs_by_name("promotion_job")
    for job in removed:
        job.schedule_removal()

    state = BotState()
    interval = state.get_promotion_interval()

    context.job_queue.run_once(
        publish_promotion,
        when=60,
        name="promotion_job_initial",
    )
    logger.info("Initial promotion scheduled in 60 seconds")

    context.job_queue.run_repeating(
        publish_promotion,
        interval=interval,
        first=interval + 60,
        name="promotion_job",
    )
    logger.info(f"Promotions scheduled to repeat every {interval} seconds ({interval / 3600} hours)")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel to authorized users."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permiso para acceder al panel de administración.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Promotion", callback_data="add_promo")],
        [InlineKeyboardButton("📋 View Promotions", callback_data="view_promos")],
        [InlineKeyboardButton("✏️ Edit Promotion", callback_data="edit_promo")],
        [InlineKeyboardButton("🗑 Delete Promotion", callback_data="delete_promo")],
        [InlineKeyboardButton("🚀 Publish Now", callback_data="publish_now")],
        [InlineKeyboardButton("⏰ Change Interval", callback_data="change_interval")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="bot_status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ **Panel de Administración**", reply_markup=reply_markup, parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks from admin panel."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return

    if query.data == "add_promo":
        await query.edit_message_text("📸 Por favor, envía una foto o video para la promoción.")
        return ADD_PHOTO

    elif query.data == "view_promos":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("No hay promociones almacenadas.")
            return
        
        text = "📋 **Promociones Actuales:**\n\n"
        for i, promo in enumerate(promos, 1):
            text += f"{i}. **ID:** `{promo['id']}`\n"
            text += f"   **Caption:** {promo.get('caption', 'Sin descripción')}\n"
            text += f"   **Admin:** @{promo.get('admin_username', 'N/A')}\n"
            text += f"   **Media:** {len(promo.get('media', []))} archivo(s)\n\n"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "edit_promo":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("No hay promociones para editar.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{p['id']}", callback_data=f"edit_{p['id']}")] for p in promos]
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Selecciona la promoción a editar:", reply_markup=reply_markup)

    elif query.data == "delete_promo":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("No hay promociones para eliminar.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{p['id']}", callback_data=f"delete_{p['id']}")] for p in promos]
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Selecciona la promoción a eliminar:", reply_markup=reply_markup)

    elif query.data == "publish_now":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("No hay promociones para publicar.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{p['id']}", callback_data=f"pub_{p['id']}")] for p in promos]
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Selecciona la promoción a publicar:", reply_markup=reply_markup)

    elif query.data == "change_interval":
        await query.edit_message_text("⏰ Envía el nuevo intervalo en segundos (ej: 7200 para 2 horas):")
        return INTERVAL_INPUT

    elif query.data == "bot_status":
        state = BotState()
        manager = PromotionsManager()
        promos = manager.get_all()
        interval = state.get_promotion_interval()
        last_published = state.get_last_published()
        
        text = "📊 **Estado del Bot:**\n\n"
        text += f"✅ Bot en línea\n"
        text += f"📦 Promociones almacenadas: {len(promos)}\n"
        text += f"⏰ Intervalo: {interval}s ({interval/3600}h)\n"
        text += f"📅 Última publicación: {last_published or 'Nunca'}\n"
        text += f"🔐 Grupo destino: `{GROUP_ID}`"
        
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data.startswith("delete_"):
        promo_id = query.data.replace("delete_", "")
        manager = PromotionsManager()
        if manager.delete(promo_id):
            await query.edit_message_text(f"✅ Promoción `{promo_id}` eliminada.", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Error al eliminar la promoción.")

    elif query.data.startswith("pub_"):
        promo_id = query.data.replace("pub_", "")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🚀 Publicando...")
        await publish_promotion(context)
        await query.edit_message_text("✅ Promoción publicada.")

    elif query.data == "cancel":
        await query.edit_message_text("Operación cancelada.")


async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive photo/video for new promotion."""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["media"] = [file_id]
        await update.message.reply_text("📝 Ahora envía la descripción/caption:")
        return ADD_CAPTION
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data["media"] = [file_id]
        await update.message.reply_text("📝 Ahora envía la descripción/caption:")
        return ADD_CAPTION
    else:
        await update.message.reply_text("❌ Por favor envía una foto o video.")
        return ADD_PHOTO


async def add_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive caption for new promotion."""
    context.user_data["caption"] = update.message.text
    await update.message.reply_text("👤 Envía el nombre de usuario del administrador (sin @):")
    return ADD_USERNAME


async def add_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive username and save promotion."""
    context.user_data["admin_username"] = update.message.text
    
    manager = PromotionsManager()
    promos = manager.get_all()
    next_id = f"promo_{str(len(promos) + 1).zfill(3)}"
    
    new_promo = {
        "id": next_id,
        "caption": context.user_data.get("caption", ""),
        "media": context.user_data.get("media", []),
        "admin_username": context.user_data.get("admin_username", "el593rm")
    }
    
    manager.add(new_promo)
    await update.message.reply_text(f"✅ Promoción `{next_id}` creada exitosamente.", parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    logger.info(f"Received /start from chat_id={update.effective_chat.id} type={update.effective_chat.type}")

    if update.effective_chat and update.effective_chat.type == "private":
        try:
            await update.message.reply_text(
                "¡Hola! Soy el bot de promociones. Estoy en funcionamiento y publicaré promociones periódicamente."
            )
            logger.info("Replied to /start in private chat")
        except Exception as e:
            logger.error(f"Failed to reply to /start: {e}")


async def post_init(application: Application):
    """Called after the application is initialized."""
    logger.info("Bot started. Scheduling promotions...")
    await schedule_promotions(application)


def main():
    """Main function to start the bot."""
    if not validate_configuration():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    logger.info("Starting Telegram Promotions Bot with Admin Panel...")
    logger.info(f"Target group ID: {GROUP_ID}")
    logger.info(f"Admin user ID: {ADMIN_USER_ID}")

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", admin_panel))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add conversation handler for adding promotions
    conv_handler = ConversationHandler(
        entry_points=[],
        states={
            ADD_PHOTO: [MessageHandler(filters.PHOTO | filters.VIDEO, add_photo)],
            ADD_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_caption)],
            ADD_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_username)],
            INTERVAL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval_input)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()


async def interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interval input."""
    try:
        interval = int(update.message.text)
        if interval < 60:
            await update.message.reply_text("❌ El intervalo mínimo es 60 segundos.")
            return INTERVAL_INPUT
        
        state = BotState()
        state.set_promotion_interval(interval)
        state.save()
        
        # Reschedule with new interval
        if context.job_queue:
            removed = context.job_queue.get_jobs_by_name("promotion_job")
            for job in removed:
                job.schedule_removal()
            
            context.job_queue.run_repeating(
                publish_promotion,
                interval=interval,
                first=interval + 60,
                name="promotion_job",
            )
        
        await update.message.reply_text(f"✅ Intervalo actualizado a {interval}s ({interval/3600}h)")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Por favor envía un número válido.")
        return INTERVAL_INPUT


if __name__ == "__main__":
    main()
