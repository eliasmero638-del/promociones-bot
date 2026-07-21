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
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from dotenv import load_dotenv
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, filters
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", 0))
ADMIN_USER_ID = 8710301236
# --- Phase 6: optional persistent storage location (Railway Volume) ---
# Backward-compatible by design: if DATA_DIR is not set, promotions.json and
# bot_state.json are stored exactly where they always were (the process's
# working directory) - existing installs keep working unchanged. If DATA_DIR
# is set (e.g. to a Railway Volume mount path), both files are stored there
# instead, so they survive redeploys/restarts instead of resetting to
# whatever promotions.json happens to be committed in git.
DATA_DIR = os.getenv("DATA_DIR", "").strip()

if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    PROMOTIONS_FILE = os.path.join(DATA_DIR, "promotions.json")
    STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
    WELCOME_CONFIG_FILE = os.path.join(DATA_DIR, "welcome_config.json")
else:
    PROMOTIONS_FILE = "promotions.json"
    STATE_FILE = "bot_state.json"
    WELCOME_CONFIG_FILE = "welcome_config.json"

# --- Phase 7: optional Upstash Redis storage (no new Railway resources) ---
# Backward-compatible by design, same principle as DATA_DIR above: if these
# two variables are not both set, PromotionsManager/BotState behave exactly
# as before (local JSON file, optionally under DATA_DIR). If both are set,
# they persist to Upstash Redis instead - an external, free-tier service
# that needs no Railway Volume or database resource. Storage backend is
# decided once per process (not per request) to avoid the two backends
# ever silently drifting out of sync with each other.
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
USE_UPSTASH = bool(UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN)

# Redis keys used to store the whole promotions.json / bot_state.json
# payload as a single JSON string each - mirrors the "one file, one blob"
# shape the local-file backend already uses, so no data model changes.
UPSTASH_PROMOTIONS_KEY = "promociones_bot:promotions"
UPSTASH_STATE_KEY = "promociones_bot:bot_state"
UPSTASH_WELCOME_CONFIG_KEY = "promociones_bot:welcome_config"


def _upstash_command(*parts) -> Optional[dict]:
    """Execute a single Upstash Redis REST command (their documented
    "POST body = JSON array" call form: e.g. _upstash_command("GET", key)).

    Returns the parsed JSON response dict on success, or None on any
    network/HTTP error. Never raises - callers treat None the same way the
    local-file backend already treats a failed read/write (log + safe
    default), so a transient Upstash issue degrades gracefully instead of
    crashing the bot.
    """
    if not USE_UPSTASH:
        return None
    try:
        response = requests.post(
            UPSTASH_REDIS_REST_URL,
            headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
            json=list(parts),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[upstash] Command '{parts[0] if parts else '?'}' failed: {e}")
        return None
PROMOTION_INTERVAL = 7200  # 2 hours

# Quality audit fix: how long (in seconds) an admin can be inactive mid-way
# through a /panel conversation (Agregar/Editar Promoción, Configurar
# Bienvenida) before it auto-cancels. Without this, abandoning a flow
# partway left the admin stuck in that state indefinitely.
CONVERSATION_TIMEOUT_SECONDS = 600  # 10 minutes

# Conversation states
# Phase 4 note: EDIT_* states are appended at the end of the range so the
# existing ADD_PHOTO/ADD_CAPTION/ADD_USERNAME/INTERVAL_INPUT values (0-3)
# stay exactly the same as before.
# Phase 6 (welcome system) note: WELCOME_* states are appended likewise, so
# values 0-7 from earlier phases are untouched.
(
    ADD_PHOTO,
    ADD_CAPTION,
    ADD_USERNAME,
    INTERVAL_INPUT,
    EDIT_MENU,
    EDIT_CAPTION_INPUT,
    EDIT_MEDIA_INPUT,
    EDIT_USERNAME_INPUT,
    WELCOME_MENU,
    WELCOME_TEXT_INPUT,
    WELCOME_IMAGE_INPUT,
    WELCOME_BUTTON_INPUT,
    WELCOME_DELETE_SECONDS_INPUT,
) = range(13)

# --- Phase 2: channel post ingestion config ---
# In-memory buffer to aggregate channel_post updates that belong to the same
# Telegram media group (album). Telegram sends each item of an album as a
# separate channel_post update sharing the same media_group_id, so we must
# accumulate them before saving a single promotion. This is transient
# runtime state only - it is never persisted to disk.
pending_media_groups: Dict[str, Dict] = {}
# How long to wait, after the last item of a media group arrives, before
# assuming the album is complete and saving it as one promotion.
MEDIA_GROUP_DEBOUNCE_SECONDS = 2.0
# Default admin contact used for promotions created automatically from
# channel posts (no admin_username is available from a channel post).
DEFAULT_ADMIN_USERNAME = "el593rm"

# --- Phase 3: integration safeguard against duplicate/split albums ---
# Remembers which media_group_id values were already turned into a
# promotion, and which promo_id they became, for a short window after
# finalizing. If a stray item for that same album arrives late (e.g. slow
# network pushed it past MEDIA_GROUP_DEBOUNCE_SECONDS), it gets appended to
# the already-saved promotion instead of creating a second, duplicate one.
recently_finalized_groups: Dict[str, Dict] = {}
RECENTLY_FINALIZED_TTL_SECONDS = 60

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

if USE_UPSTASH:
    logger.info(
        f"[storage] Upstash Redis configured. Using persistent storage in Upstash "
        f"(keys '{UPSTASH_PROMOTIONS_KEY}' / '{UPSTASH_STATE_KEY}'). Local files are not used."
    )
elif DATA_DIR:
    logger.info(
        f"[storage] DATA_DIR is set ('{DATA_DIR}'). Using persistent storage: "
        f"promotions='{PROMOTIONS_FILE}' state='{STATE_FILE}'."
    )
else:
    logger.info(
        f"[storage] Neither Upstash nor DATA_DIR is set. Using local, non-persistent storage: "
        f"promotions='{PROMOTIONS_FILE}' state='{STATE_FILE}'. "
        f"This will reset on the next redeploy/restart unless configured otherwise."
    )


class PromotionsManager:
    """Manages promotions, stored either in Upstash Redis (if configured) or
    in a local JSON file (fallback - identical to the original behavior)."""

    def __init__(self, file_path: str = PROMOTIONS_FILE):
        self.file_path = file_path
        self.use_upstash = USE_UPSTASH
        backend = "Upstash Redis" if self.use_upstash else f"local file ({self.file_path})"
        logger.info(f"[PromotionsManager.__init__] Creating manager. Storage backend: {backend}")
        self.data = self._load()
        logger.info(f"[PromotionsManager.__init__] Loaded {len(self.data.get('promotions', []))} promotions from {backend}")

    def _load(self) -> dict:
        """Load promotions from the active backend (Upstash Redis or local file)."""
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        logger.info(f"[PromotionsManager._load] Starting load from Upstash Redis, key: {UPSTASH_PROMOTIONS_KEY}")
        result = _upstash_command("GET", UPSTASH_PROMOTIONS_KEY)

        if result is None:
            logger.error("[PromotionsManager._load] Upstash Redis request failed; starting with an empty list for this session.")
            return {"promotions": []}

        raw = result.get("result")
        if raw is None:
            logger.info("[PromotionsManager._load] No promotions stored yet in Upstash Redis; starting empty.")
            return {"promotions": []}

        try:
            data = json.loads(raw)
            logger.info(f"[PromotionsManager._load] Successfully loaded from Upstash, contains {len(data.get('promotions', []))} promotions")
            return data
        except Exception as e:
            logger.error(f"[PromotionsManager._load] Failed to parse JSON from Upstash: {e}")
            return {"promotions": []}

    def _load_from_file(self) -> dict:
        """Load promotions from JSON file."""
        logger.info(f"[PromotionsManager._load] Starting load from: {self.file_path}")
        if Path(self.file_path).exists():
            try:
                logger.info(f"[PromotionsManager._load] File exists, opening for reading")
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                logger.info(f"[PromotionsManager._load] Successfully loaded JSON, contains {len(data.get('promotions', []))} promotions")
                return data
            except Exception as e:
                logger.warning(f"[PromotionsManager._load] Failed to load promotions file: {e}")
        else:
            logger.warning(f"[PromotionsManager._load] File does not exist: {self.file_path}")
        return {"promotions": []}

    def save(self) -> bool:
        """Save promotions to the active backend (Upstash Redis or local file).

        Returns:
            bool: True on success, False on failure.
        """
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        promos_count = len(self.data.get("promotions", []))
        logger.info(f"[PromotionsManager.save] ========== SAVE START (Upstash Redis) ==========")
        logger.info(f"[PromotionsManager.save] Number of promotions to save: {promos_count}")

        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[PromotionsManager.save] ========== SAVE FAILED ==========")
            logger.error(f"[PromotionsManager.save] Could not serialize data to JSON: {e}")
            return False

        result = _upstash_command("SET", UPSTASH_PROMOTIONS_KEY, payload)

        if result is not None and result.get("result") == "OK":
            logger.info(f"[PromotionsManager.save] Upstash SET confirmed OK for {promos_count} promotions.")
            logger.info(f"[PromotionsManager.save] ========== SAVE SUCCESS ==========")
            return True

        logger.error(f"[PromotionsManager.save] ========== SAVE FAILED ==========")
        logger.error(f"[PromotionsManager.save] Upstash SET did not confirm success. Response: {result}")
        return False

    def _save_to_file(self) -> bool:
        """Save promotions to JSON file.
        
        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Debug log: before write
            abs_path = os.path.abspath(self.file_path)
            cwd = os.getcwd()
            promos_before = len(self.data.get("promotions", []))
            
            logger.info(f"[PromotionsManager.save] ========== SAVE START ==========")
            logger.info(f"[PromotionsManager.save] Absolute file path: {abs_path}")
            logger.info(f"[PromotionsManager.save] Current working directory: {cwd}")
            logger.info(f"[PromotionsManager.save] Number of promotions before save: {promos_before}")
            logger.info(f"[PromotionsManager.save] Data structure: {self.data}")
            
            # Write file
            logger.info(f"[PromotionsManager.save] About to call json.dump() to write file")
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                logger.info(f"[PromotionsManager.save] json.dump() completed, now flushing buffer")
                # CRITICAL FIX: Flush the file buffer to ensure data is written
                f.flush()
                logger.info(f"[PromotionsManager.save] f.flush() completed, now syncing to disk")
                # CRITICAL FIX: Sync to disk at OS level to persist changes
                os.fsync(f.fileno())
                logger.info(f"[PromotionsManager.save] os.fsync() completed, write is now persisted to disk")
            logger.info(f"[PromotionsManager.save] json.dump() + flush + fsync all completed successfully")
            
            # Debug log: after write
            promos_after = len(self.data.get("promotions", []))
            logger.info(f"[PromotionsManager.save] Number of promotions after json.dump(): {promos_after}")
            
            # Verify: immediately reopen and check
            try:
                logger.info(f"[PromotionsManager.save] Starting verification - reopening file to verify write")
                with open(self.file_path, "r") as f:
                    verify_data = json.load(f)
                verify_count = len(verify_data.get("promotions", []))
                logger.info(f"[PromotionsManager.save] Verification read completed - found {verify_count} promotions in file")
                logger.info(f"[PromotionsManager.save] Verify data structure: {verify_data}")
                
                if verify_count != promos_after:
                    logger.error(f"[PromotionsManager.save] VERIFY FAILED - Expected {promos_after} promotions, but found {verify_count} in file")
                    return False
                
                logger.info(f"[PromotionsManager.save] Verification succeeded: {verify_count} promotions confirmed in file")
            except Exception as verify_error:
                logger.error(f"[PromotionsManager.save] VERIFY FAILED - Could not reopen file for verification: {verify_error}")
                logger.error(f"[PromotionsManager.save] Verification traceback: {traceback.format_exc()}")
                return False
            
            logger.info(f"[PromotionsManager.save] ========== SAVE SUCCESS ==========")
            return True
            
        except Exception as e:
            logger.error(f"[PromotionsManager.save] ========== SAVE FAILED ==========")
            logger.error(f"[PromotionsManager.save] Exception: {e}")
            logger.error(f"[PromotionsManager.save] Exception type: {type(e).__name__}")
            logger.error(f"[PromotionsManager.save] Traceback:\n{traceback.format_exc()}")
            return False

    def get_all(self) -> List[Dict]:
        """Get all promotions."""
        return self.data.get("promotions", [])

    def get_by_id(self, promo_id: str) -> Optional[Dict]:
        """Get promotion by ID."""
        for promo in self.get_all():
            if promo.get("id") == promo_id:
                return promo
        return None

    def add(self, promotion: Dict) -> bool:
        """Add a new promotion.
        
        Args:
            promotion: Dictionary containing promotion data.
            
        Returns:
            bool: True if promotion was added and saved successfully, False otherwise.
        """
        logger.info(f"[PromotionsManager.add] ========== ADD START ==========")
        logger.info(f"[PromotionsManager.add] Adding promotion: {promotion}")
        logger.info(f"[PromotionsManager.add] Current promotions count before append: {len(self.data.get('promotions', []))}")
        
        self.data["promotions"].append(promotion)
        
        logger.info(f"[PromotionsManager.add] Promotion appended to memory, count now: {len(self.data.get('promotions', []))}")
        logger.info(f"[PromotionsManager.add] Calling save() to persist to file")
        
        save_result = self.save()
        
        logger.info(f"[PromotionsManager.add] save() returned: {save_result}")
        logger.info(f"[PromotionsManager.add] ========== ADD END ==========")
        
        return save_result

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
    """Manages the bot state (message IDs and current promotion), stored
    either in Upstash Redis (if configured) or in a local JSON file
    (fallback - identical to the original behavior)."""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.use_upstash = USE_UPSTASH
        backend = "Upstash Redis" if self.use_upstash else f"local file ({self.state_file})"
        logger.info(f"[BotState.__init__] Creating state manager. Storage backend: {backend}")
        self.data = self._load()

    def _default_state(self) -> dict:
        return {
            "current_promotion_index": 0,
            "last_album_message_id": None,
            "last_button_message_id": None,
            "last_pinned_message_id": None,
            "last_published": None,
            "promotion_interval": PROMOTION_INTERVAL,
        }

    def _load(self) -> dict:
        """Load state from the active backend (Upstash Redis or local file)."""
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        result = _upstash_command("GET", UPSTASH_STATE_KEY)

        if result is None:
            logger.error("[BotState._load] Upstash Redis request failed; starting with default state for this session.")
            return self._default_state()

        raw = result.get("result")
        if raw is None:
            logger.info("[BotState._load] No state stored yet in Upstash Redis; starting with default state.")
            return self._default_state()

        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[BotState._load] Failed to parse JSON from Upstash: {e}")
            return self._default_state()

    def _load_from_file(self) -> dict:
        """Load state from JSON file."""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return self._default_state()

    def save(self):
        """Save state to the active backend (Upstash Redis or local file)."""
        if self.use_upstash:
            self._save_to_upstash()
        else:
            self._save_to_file()

    def _save_to_upstash(self):
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[BotState.save] Could not serialize state to JSON: {e}")
            return

        result = _upstash_command("SET", UPSTASH_STATE_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info("[BotState.save] State saved successfully to Upstash Redis.")
        else:
            logger.error(f"[BotState.save] Upstash SET did not confirm success. Response: {result}")

    def _save_to_file(self):
        """Save state to JSON file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.data, f, indent=2)
                logger.info("State file flushing buffer")
                f.flush()
                logger.info("State file syncing to disk")
                os.fsync(f.fileno())
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

    def get_last_pinned_message_id(self) -> Optional[int]:
        """The message_id the bot last *confirmed* pinning successfully -
        distinct from last_button_message_id (which is set whenever a
        button message is sent, regardless of whether pinning it actually
        succeeded). Used to tell "a message the bot pinned" apart from one
        an admin pinned manually. See _unpin_previous_promotion_message()."""
        return self.data.get("last_pinned_message_id")

    def set_last_pinned_message_id(self, message_id: Optional[int]):
        self.data["last_pinned_message_id"] = message_id

    def get_last_published(self) -> Optional[str]:
        return self.data.get("last_published")

    def set_last_published(self, timestamp: str):
        self.data["last_published"] = timestamp

    def get_promotion_interval(self) -> int:
        return self.data.get("promotion_interval", PROMOTION_INTERVAL)

    def set_promotion_interval(self, interval: int):
        self.data["promotion_interval"] = interval


# --- Phase 6: welcome-system configuration ---
DEFAULT_WELCOME_TEXT = (
    "👋 ¡Bienvenido(a), {nombre}!\n\n"
    "Gracias por unirte al grupo.\n\n"
    "Lee las reglas y disfruta del contenido."
)

# Order here also defines the order of the "edit button" menu options.
WELCOME_BUTTON_LABELS = {
    "sell_url": "💳 Comprar VIP",
    "contact_url": "💬 Contactar Administrador",
    "rules_url": "📖 Reglas",
    "channel_url": "🌐 Canal Oficial",
}


class WelcomeConfigManager:
    """Manages the welcome-system configuration (on/off, text, image,
    button URLs, auto-delete delay), stored either in Upstash Redis (if
    configured) or in a local JSON file - the exact same dual-backend
    pattern already used by PromotionsManager and BotState, so it inherits
    the same persistence guarantees (and the same local-file fallback)
    without introducing a new storage mechanism."""

    def __init__(self, file_path: str = WELCOME_CONFIG_FILE):
        self.file_path = file_path
        self.use_upstash = USE_UPSTASH
        self.data = self._load()

    def _default_config(self) -> dict:
        return {
            "enabled": True,
            "welcome_text": DEFAULT_WELCOME_TEXT,
            "welcome_image_file_id": None,
            "delete_after_seconds": 60,
            "buttons": {
                "sell_url": f"https://t.me/{DEFAULT_ADMIN_USERNAME}",
                "contact_url": f"https://t.me/{DEFAULT_ADMIN_USERNAME}",
                "rules_url": "",
                "channel_url": "",
            },
        }

    def _merge_with_defaults(self, data: dict) -> dict:
        merged = self._default_config()
        merged.update(data)
        merged["buttons"] = {**self._default_config()["buttons"], **data.get("buttons", {})}
        return merged

    def _load(self) -> dict:
        if self.use_upstash:
            return self._load_from_upstash()
        return self._load_from_file()

    def _load_from_upstash(self) -> dict:
        result = _upstash_command("GET", UPSTASH_WELCOME_CONFIG_KEY)

        if result is None:
            logger.error("[WelcomeConfigManager._load] Upstash Redis request failed; using default config for this session.")
            return self._default_config()

        raw = result.get("result")
        if raw is None:
            logger.info("[WelcomeConfigManager._load] No welcome config stored yet in Upstash Redis; using defaults.")
            return self._default_config()

        try:
            return self._merge_with_defaults(json.loads(raw))
        except Exception as e:
            logger.error(f"[WelcomeConfigManager._load] Failed to parse JSON from Upstash: {e}")
            return self._default_config()

    def _load_from_file(self) -> dict:
        if Path(self.file_path).exists():
            try:
                with open(self.file_path, "r") as f:
                    return self._merge_with_defaults(json.load(f))
            except Exception as e:
                logger.warning(f"[WelcomeConfigManager._load] Failed to load welcome config file: {e}")
        return self._default_config()

    def save(self) -> bool:
        if self.use_upstash:
            return self._save_to_upstash()
        return self._save_to_file()

    def _save_to_upstash(self) -> bool:
        try:
            payload = json.dumps(self.data)
        except Exception as e:
            logger.error(f"[WelcomeConfigManager.save] Could not serialize welcome config: {e}")
            return False

        result = _upstash_command("SET", UPSTASH_WELCOME_CONFIG_KEY, payload)
        if result is not None and result.get("result") == "OK":
            logger.info("[WelcomeConfigManager.save] Welcome config saved to Upstash Redis.")
            return True

        logger.error(f"[WelcomeConfigManager.save] Upstash SET did not confirm success: {result}")
        return False

    def _save_to_file(self) -> bool:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logger.info("[WelcomeConfigManager.save] Welcome config saved to local file.")
            return True
        except Exception as e:
            logger.error(f"[WelcomeConfigManager.save] Failed to save welcome config file: {e}")
            return False

    def is_enabled(self) -> bool:
        return bool(self.data.get("enabled", True))

    def set_enabled(self, enabled: bool):
        self.data["enabled"] = enabled

    def get_welcome_text(self) -> str:
        return self.data.get("welcome_text", DEFAULT_WELCOME_TEXT)

    def set_welcome_text(self, text: str):
        self.data["welcome_text"] = text

    def get_welcome_image_file_id(self) -> Optional[str]:
        return self.data.get("welcome_image_file_id")

    def set_welcome_image_file_id(self, file_id: Optional[str]):
        self.data["welcome_image_file_id"] = file_id

    def get_delete_after_seconds(self) -> int:
        return int(self.data.get("delete_after_seconds", 60))

    def set_delete_after_seconds(self, seconds: int):
        self.data["delete_after_seconds"] = seconds

    def get_button_url(self, key: str) -> str:
        return self.data.get("buttons", {}).get(key, "")

    def set_button_url(self, key: str, url: str):
        self.data.setdefault("buttons", {})[key] = url


def validate_configuration() -> bool:
    """Validate that all required configuration is set."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set")
        return False
    if not GROUP_ID or GROUP_ID == 0:
        logger.error("GROUP_ID environment variable not set or invalid")
        return False
    return True


async def _unpin_previous_promotion_message(context: ContextTypes.DEFAULT_TYPE, state: BotState):
    """Unpin the bot's own previous promotion message - and ONLY the bot's
    own message, never a message an admin pinned manually.

    Design (explicit requirement): the previous approach used
    unpin_all_chat_messages(), which clears every pinned message in the
    chat regardless of who pinned it - simple and robust against
    accumulation, but it could also wipe out a message an admin pinned by
    hand. That trade-off is no longer acceptable, so this asks Telegram
    what is CURRENTLY pinned via get_chat() and compares it against
    BotState's last_pinned_message_id - which is only ever set after a
    pin_chat_message() call is confirmed successful (see publish_promotion()
    below), never merely "the last button message sent". That distinction
    matters: if a previous pin attempt failed (e.g. the bot temporarily
    lacked permission), last_pinned_message_id still correctly points at
    whatever the bot last *actually* pinned, rather than a message that
    was never really pinned - so this stays accurate even across failed
    attempts, not just successful ones.

    - If the currently pinned message matches the bot's own last
      confirmed pin -> unpin it, and the new promotion below gets pinned
      in its place (the intended "exactly one bot-managed pin" behavior).
    - If the currently pinned message is anything else (including
      nothing, or a message an admin pinned by hand) -> leave it
      completely untouched. The new promotion is still published, and
      still gets a pin attempt below, but nothing already pinned is
      removed. In that case the chat may end up with the admin's pin
      plus the bot's new one - a deliberate trade-off in favor of never
      touching content the admin placed there themselves.
    - If get_chat() itself fails (network error, etc.), we can't verify
      what's currently pinned, so - to stay on the safe side of "never
      touch an admin's pin without confirmation" - this falls back to not
      unpinning anything for this cycle.
    """
    last_pinned_by_bot = state.get_last_pinned_message_id()
    if not last_pinned_by_bot:
        return  # the bot has never confirmed pinning anything - nothing of ours to consider unpinning

    try:
        chat = await context.bot.get_chat(chat_id=GROUP_ID)
        currently_pinned = getattr(chat, "pinned_message", None)
        currently_pinned_id = currently_pinned.message_id if currently_pinned else None
    except TelegramError as e:
        logger.warning(
            f"[pin] Could not check the chat's current pin via get_chat() ({e}); "
            f"leaving any existing pin untouched this cycle to be safe."
        )
        return

    if currently_pinned_id != last_pinned_by_bot:
        logger.info(
            f"[pin] Currently pinned message ({currently_pinned_id}) is not the bot's own last "
            f"pinned promotion ({last_pinned_by_bot}) - likely pinned manually by an admin. "
            f"Leaving it untouched; the new promotion will still be published and pinned."
        )
        return

    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=last_pinned_by_bot)
        logger.info(f"[pin] Unpinned the bot's own previous promotion message: {last_pinned_by_bot}")
        state.set_last_pinned_message_id(None)
    except TelegramError as e:
        logger.warning(f"[pin] Could not unpin previous message {last_pinned_by_bot} (may already be unpinned/deleted): {e}")


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


async def _send_promotion_media_item(context: ContextTypes.DEFAULT_TYPE, chat_id: int, media_type_hint: str, file_id: str, caption: str):
    """Send one promotion media item (photo or video), robust to an
    incorrect/unknown type hint.

    Root cause of the "media never publishes, only the caption text does"
    bug: promotions created through the admin panel's original "Agregar
    Promoción" flow (add_photo/add_username) store media as a *plain
    string* file_id - the "photo" vs "video" distinction that add_photo()
    captures in context.user_data["media_type"] is never written into the
    saved promotion. publish_promotion() then has no reliable way to know
    the real type for those entries, so its old logic just assumed
    "photo" for every plain string. For a promotion whose media is
    actually a video, that made it call send_photo() with a video file_id,
    Telegram's Bot API rejects that (wrong file identifier for the
    endpoint), the per-item TelegramError was caught and the item was
    skipped - so with no media item left to send, publish_promotion()
    fell back to its "no media could be sent" branch and sent caption-only
    text. Promotions saved with an explicit {"type": ..., "file_id": ...}
    (channel ingestion, and the admin panel's edit flow) were unaffected,
    since their type is known up front.

    Per this phase's scope, publish_promotion()/the sending path is fixed
    here without touching how promotions are saved: this function tries
    the endpoint matching media_type_hint first and, only if Telegram
    rejects the file_id for that endpoint, retries with the other media
    endpoint before giving up. This covers legacy plain-string entries of
    either real type without needing to change their stored format.
    """
    send_as_photo = lambda: context.bot.send_photo(
        chat_id=chat_id, photo=file_id, caption=caption, parse_mode="Markdown"
    )
    send_as_video = lambda: context.bot.send_video(
        chat_id=chat_id, video=file_id, caption=caption, parse_mode="Markdown"
    )

    attempts = [send_as_video, send_as_photo] if media_type_hint == "video" else [send_as_photo, send_as_video]

    last_error = None
    for attempt_index, send_attempt in enumerate(attempts):
        try:
            return await send_attempt()
        except TelegramError as e:
            last_error = e
            if attempt_index == 0:
                logger.warning(
                    f"[publish_media] Sending file_id as '{media_type_hint}' failed ({e}); "
                    f"retrying as the other media type before giving up."
                )
            continue

    raise last_error


async def publish_promotion(context: ContextTypes.DEFAULT_TYPE):
    """Publish the current valid promotion from promotions.json using Telegram file_id."""
    state = BotState()
    promotions_manager = PromotionsManager()
    all_promotions = promotions_manager.get_all()

    # Build list of valid promotions: non-empty caption OR at least one media file
    def _has_valid_media(promo: Dict) -> bool:
        media = promo.get("media", [])
        if not isinstance(media, list):
            return False

        return any(
            ((m.get("file_id") if isinstance(m, dict) else m) or "").strip()
            for m in media
            if isinstance(m, (dict, str))
        )

    valid_promotions = [
        p for p in all_promotions
        if str(p.get("caption", "") or "").strip() or _has_valid_media(p)
    ]

    if not valid_promotions:
        logger.warning("No valid promotions found.")
        return

    await _unpin_previous_promotion_message(context, state)
    await delete_previous_messages(context, state)

    promotion_index = state.get_current_promotion_index()
    if promotion_index >= len(valid_promotions):
        promotion_index = 0
        state.set_current_promotion_index(0)
        state.save()

    promotion = valid_promotions[promotion_index]

    logger.info(f"Publishing promotion {promotion['id']} ({promotion_index + 1}/{len(valid_promotions)})")

    button_message = None

    try:
        caption = promotion.get("caption", "")
        media_list = promotion.get("media", [])

        logger.info(f"[DEBUG] Complete media object: {media_list}")
        logger.info(f"[DEBUG] Media list type: {type(media_list)}, length: {len(media_list)}")

        if media_list:
            # Send each media item with caption only on first
            album_messages = []
            
            for idx, media_item in enumerate(media_list):
                try:
                    # Determine media type by checking if it's stored with type info
                    # If media_item is a dict with type and id, use that; otherwise assume photo
                    if isinstance(media_item, dict):
                        media_type = media_item.get("type", "photo")
                        file_id = media_item.get("file_id")
                    else:
                        # media_item is a plain string file_id
                        media_type = "photo"
                        file_id = media_item

                    logger.info(f"[DEBUG] Media item #{idx}: {media_item}")
                    logger.info(f"[DEBUG] Detected media type: {media_type}")
                    logger.info(f"[DEBUG] Extracted file_id: {file_id}")

                    if not file_id:
                        logger.warning(f"[DEBUG] Skipping media item {idx}: no file_id found")
                        continue

                    # Add caption only to first media item
                    item_caption = caption if idx == 0 else ""

                    if media_type == "video":
                        msg = await _send_promotion_media_item(
                            context, GROUP_ID, "video", file_id, item_caption
                        )
                    else:  # photo
                        msg = await _send_promotion_media_item(
                            context, GROUP_ID, "photo", file_id, item_caption
                        )
                    
                    album_messages.append(msg)
                    logger.info(f"Published {media_type} with file_id: {file_id}")
                
                except TelegramError as e:
                    logger.error(f"[TELEGRAM ERROR] Failed to send media {media_item}: {e}")
                    logger.error(f"[TRACEBACK] {type(e).__name__}: {str(e)}")
                    logger.error(f"[FULL TRACEBACK] {traceback.format_exc()}")
                    continue

            if album_messages:
                state.set_last_album_message_id(album_messages[0].message_id)
                logger.info(f"Album published with {len(album_messages)} messages")
            else:
                # No media could be sent, fall back to text
                text_message = await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=caption,
                    parse_mode="Markdown",
                )
                state.set_last_album_message_id(text_message.message_id)
                logger.info("Published promotion as text (no valid media files)")
        else:
            # No media configured, send as text only
            text_message = await context.bot.send_message(
                chat_id=GROUP_ID,
                text=caption,
                parse_mode="Markdown",
            )
            state.set_last_album_message_id(text_message.message_id)
            logger.info("Published promotion as text (no media configured)")

        # Send admin contact button
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

        # Pin button message
        if button_message:
            try:
                await context.bot.pin_chat_message(
                    chat_id=GROUP_ID,
                    message_id=button_message.message_id,
                    disable_notification=True,
                )
                logger.info(f"Pinned button message: {button_message.message_id}")
                state.set_last_pinned_message_id(button_message.message_id)
            except TelegramError as e:
                logger.warning(f"Could not pin message: {e}")

        # Update state for next valid promotion
        next_index = (promotion_index + 1) % len(valid_promotions)
        state.set_current_promotion_index(next_index)
        state.set_last_published(datetime.now().isoformat())
        state.save()

        logger.info(f"Promotion published successfully. Next promotion index: {next_index}")

    except TelegramError as e:
        logger.error(f"[TELEGRAM ERROR] Failed to publish promotion: {e}")
        logger.error(f"[TRACEBACK] {type(e).__name__}: {str(e)}")
        logger.error(f"[FULL TRACEBACK] {traceback.format_exc()}")
    except Exception as e:
        logger.error(f"[UNEXPECTED ERROR] Unexpected error while publishing promotion: {e}")
        logger.error(f"[TRACEBACK] {type(e).__name__}: {str(e)}")
        logger.error(f"[FULL TRACEBACK] {traceback.format_exc()}")


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


async def conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when the main /panel conversation (Agregar/Editar Promoción,
    Configurar Bienvenida) times out after CONVERSATION_TIMEOUT_SECONDS of
    inactivity. Quality-audit fix: clears any partial state so the admin
    isn't left stuck in a half-finished flow, and lets them know /panel is
    available again."""
    context.user_data.clear()
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "⏱️ La operación se canceló automáticamente por inactividad. Usa /panel para empezar de nuevo."
            )
        elif update.message:
            await update.message.reply_text(
                "⏱️ La operación se canceló automáticamente por inactividad. Usa /panel para empezar de nuevo."
            )
    except TelegramError as e:
        logger.warning(f"[conversation_timeout] Could not notify admin of timeout: {e}")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel to authorized users."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permiso para acceder al panel de administración.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Agregar Promoción", callback_data="add_promo")],
        [InlineKeyboardButton("📋 Ver Promociones", callback_data="view_promos")],
        [InlineKeyboardButton("✏️ Editar Promoción", callback_data="edit_promo")],
        [InlineKeyboardButton("🗑 Eliminar Promoción", callback_data="delete_promo")],
        [InlineKeyboardButton("🚀 Publicar Ahora", callback_data="publish_now")],
        [InlineKeyboardButton("⏰ Cambiar Intervalo", callback_data="change_interval")],
        [InlineKeyboardButton("👋 Configurar Bienvenida", callback_data="welcome_config")],
        [InlineKeyboardButton("📊 Estado del Bot", callback_data="bot_status")],
        [InlineKeyboardButton("🔧 Debug Storage", callback_data="debug_storage")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ **Panel de Administración**", reply_markup=reply_markup, parse_mode="Markdown")


async def debug_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /debug_storage command and button callback."""
    if update.effective_user.id != ADMIN_USER_ID:
        if update.callback_query:
            await update.callback_query.answer("❌ No tienes permiso.", show_alert=True)
        else:
            await update.message.reply_text("❌ No tienes permiso para ejecutar este comando.")
        return

    # Gather debug information
    cwd = os.getcwd()
    abs_path = os.path.abspath(PROMOTIONS_FILE)
    file_exists = os.path.exists(abs_path)
    file_size = os.path.getsize(abs_path) if file_exists else 0
    
    manager = PromotionsManager()
    all_promos = manager.get_all()
    num_promos = len(all_promos)
    first_promo_id = all_promos[0].get("id") if all_promos else "N/A"
    last_promo_id = all_promos[-1].get("id") if all_promos else "N/A"
    
    # Load raw file contents
    try:
        with open(abs_path, "r") as f:
            raw_contents = f.read()
    except Exception as e:
        raw_contents = f"Error reading file: {e}"

    # Format message for Telegram
    debug_message = (
        "🔧 **DEBUG STORAGE INFORMATION**\n\n"
        f"📂 Current Working Directory:\n`{cwd}`\n\n"
        f"📄 Absolute Path to promotions.json:\n`{abs_path}`\n\n"
        f"✅ File Exists: {file_exists}\n\n"
        f"📊 File Size: {file_size} bytes\n\n"
        f"📦 Number of Promotions: {num_promos}\n\n"
        f"🆔 First Promotion ID: `{first_promo_id}`\n\n"
        f"🆔 Last Promotion ID: `{last_promo_id}`\n\n"
        f"📋 **Raw File Contents:**\n"
        f"```json\n{raw_contents}\n```"
    )

    # Log to Railway logs
    logger.info("=" * 80)
    logger.info("🔧 DEBUG STORAGE INFORMATION")
    logger.info("=" * 80)
    logger.info(f"Current Working Directory: {cwd}")
    logger.info(f"Absolute Path to promotions.json: {abs_path}")
    logger.info(f"File Exists: {file_exists}")
    logger.info(f"File Size: {file_size} bytes")
    logger.info(f"Number of Promotions: {num_promos}")
    logger.info(f"First Promotion ID: {first_promo_id}")
    logger.info(f"Last Promotion ID: {last_promo_id}")
    logger.info(f"Raw File Contents:\n{raw_contents}")
    logger.info("=" * 80)

    # Send message
    if update.callback_query:
        await update.callback_query.edit_message_text(debug_message, parse_mode="Markdown")
    else:
        await update.message.reply_text(debug_message, parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks from admin panel."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return

    if query.data == "add_promo":
        await query.edit_message_text("📸 Por favor, envía una foto o un video para la promoción.")
        context.user_data.clear()
        return ADD_PHOTO

    elif query.data == "view_promos":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("❌ No hay promociones almacenadas.")
            return
        
        text = "📋 **Promociones Actuales:**\n\n"
        for i, promo in enumerate(promos, 1):
            text += f"{i}. **ID:** `{promo['id']}`\n"
            text += f"   **Descripción:** {promo.get('caption', 'Sin descripción')}\n"
            text += f"   **Admin:** @{promo.get('admin_username', 'N/A')}\n"
            text += f"   **Archivos:** {len(promo.get('media', []))} archivo(s)\n\n"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "edit_promo":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("❌ No hay promociones para editar.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{p['id']}", callback_data=f"edit_select_{p['id']}")] for p in promos]
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Selecciona la promoción a editar:", reply_markup=reply_markup)

    elif query.data == "delete_promo":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("❌ No hay promociones para eliminar.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{p['id']}", callback_data=f"delete_{p['id']}")] for p in promos]
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Selecciona la promoción a eliminar:", reply_markup=reply_markup)

    elif query.data == "publish_now":
        manager = PromotionsManager()
        promos = manager.get_all()
        if not promos:
            await query.edit_message_text("❌ No hay promociones para publicar.")
            return
        
        # Publish immediately without selection dialog
        await query.edit_message_text("🚀 Publicando promoción...")
        await publish_promotion(context)
        await query.edit_message_text("✅ Promoción publicada correctamente.")

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

    elif query.data == "debug_storage":
        await debug_storage(update, context)

    elif query.data.startswith("delete_"):
        promo_id = query.data.replace("delete_", "")
        manager = PromotionsManager()
        if manager.delete(promo_id):
            await query.edit_message_text(f"✅ Promoción `{promo_id}` eliminada correctamente.", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Error al eliminar la promoción.")

    elif query.data == "cancel":
        # Integration fix (Phase 4): this branch is used as the fallback for
        # conv_handler (add_promo / change_interval / edit_select_* flows).
        # It previously returned None, which does not end a ConversationHandler
        # conversation, leaving the user "stuck" in the last state after
        # pressing Cancelar. Clearing user_data avoids leaking a half-finished
        # edit/add into whatever conversation starts next.
        context.user_data.clear()
        await query.edit_message_text("❌ Operación cancelada.")
        return ConversationHandler.END


async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive photo/video for new promotion."""
    logger.info(f"[add_photo] called. Has photo: {bool(update.message.photo)}, Has video: {bool(update.message.video)}")
    
    if update.message.photo:
        # Get the highest resolution photo
        file_id = update.message.photo[-1].file_id
        # Store as plain string - media type will be inferred as photo
        context.user_data["media"] = [file_id]
        context.user_data["media_type"] = "photo"
        logger.info(f"[add_photo] Photo received with file_id: {file_id}")
        await update.message.reply_text("📝 Ahora envía el texto de la promoción:")
        return ADD_CAPTION
    elif update.message.video:
        file_id = update.message.video.file_id
        # Store as plain string - media type will be inferred as video
        context.user_data["media"] = [file_id]
        context.user_data["media_type"] = "video"
        logger.info(f"[add_photo] Video received with file_id: {file_id}")
        await update.message.reply_text("📝 Ahora envía el texto de la promoción:")
        return ADD_CAPTION
    else:
        logger.warning("[add_photo] Invalid message type for add_photo")
        await update.message.reply_text("❌ Por favor envía una foto o un video.")
        return ADD_PHOTO


async def add_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive caption for new promotion."""
    caption_text = update.message.text
    context.user_data["caption"] = caption_text
    logger.info(f"[add_caption] Caption received: {caption_text}")
    logger.info(f"[add_caption] Current user_data media: {context.user_data.get('media')}")
    await update.message.reply_text("👤 Escribe el usuario de Telegram del administrador (sin @):")
    return ADD_USERNAME


async def add_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive username and save promotion."""
    logger.info(f"[add_username] ========== ADD_USERNAME START ==========")
    
    admin_username = update.message.text
    context.user_data["admin_username"] = admin_username
    logger.info(f"[add_username] Username received: {admin_username}")
    logger.info(f"[add_username] User data before saving: {context.user_data}")
    
    logger.info(f"[add_username] Creating new PromotionsManager instance")
    manager = PromotionsManager()
    
    logger.info(f"[add_username] Calling manager.get_all()")
    promos = manager.get_all()
    logger.info(f"[add_username] Got {len(promos)} existing promotions")
    
    next_id = f"promo_{str(len(promos) + 1).zfill(3)}"
    logger.info(f"[add_username] Next promotion ID will be: {next_id}")
    
    # Get media from context.user_data
    media = context.user_data.get("media", [])
    caption = context.user_data.get("caption", "")
    
    logger.info(f"[add_username] Media: {media}")
    logger.info(f"[add_username] Caption: {caption}")
    logger.info(f"[add_username] Creating promotion with media: {media}, caption: {caption}")
    
    new_promo = {
        "id": next_id,
        "caption": caption,
        "media": media,
        "admin_username": admin_username
    }
    logger.info(f"[add_username] New promotion object: {new_promo}")
    
    # Save and check result
    logger.info(f"[add_username] Calling manager.add(new_promo)")
    add_result = manager.add(new_promo)
    logger.info(f"[add_username] manager.add() returned: {add_result}")
    
    if not add_result:
        # Save failed
        logger.error(f"[add_username] ❌ Failed to save promotion {next_id}")
        await update.message.reply_text("❌ Failed to save promotion.", parse_mode="Markdown")
    else:
        # Save succeeded
        logger.info(f"[add_username] ✅ Promotion created: {next_id} with {len(media)} media file(s)")
        await update.message.reply_text(f"✅ Promoción `{next_id}` creada correctamente.", parse_mode="Markdown")
    
    logger.info(f"[add_username] ========== ADD_USERNAME END ==========")
    
    context.user_data.clear()
    return ConversationHandler.END


# --- Phase 6: welcome-system for new group members ---
#
# Design: handle_new_chat_member() is a MessageHandler on Telegram's
# "new_chat_members" service message, scoped to GROUP_ID only. It reads
# WelcomeConfigManager (same Upstash/local-file backend as everything
# else) to build the message (text with {nombre} replaced by a clickable
# mention, optional image, configurable buttons) and schedules its own
# deletion via JobQueue - the same run_once() debounce mechanism already
# used for media-group ingestion (Phase 2/3). The "👋 Configurar
# Bienvenida" panel flow follows the exact same ConversationHandler shape
# as the "✏️ Editar Promoción" flow (Phase 4): an entry point, a menu
# state, and one input state per field - except each field here saves
# immediately when received (simple settings, not a multi-field object
# that needs an all-or-nothing "Guardar Cambios" step).

def _build_welcome_keyboard(config: WelcomeConfigManager) -> Optional[InlineKeyboardMarkup]:
    """Build the welcome message's button row from configured URLs.
    Buttons with no URL configured yet are simply omitted, so an
    unconfigured link never renders as a broken button."""
    rows = []
    for key, label in WELCOME_BUTTON_LABELS.items():
        url = config.get_button_url(key)
        if url:
            rows.append([InlineKeyboardButton(label, url=url)])
    return InlineKeyboardMarkup(rows) if rows else None


async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members of the promotions group (GROUP_ID) with a
    configurable image + text + buttons, auto-deleted after a configurable
    delay. Bots (including this one being (re)added) are skipped."""
    message = update.message
    if message is None or message.new_chat_members is None:
        return
    if message.chat_id != GROUP_ID:
        return

    config = WelcomeConfigManager()
    if not config.is_enabled():
        logger.info("[welcome] Welcome system is disabled; skipping new member(s).")
        return

    keyboard = _build_welcome_keyboard(config)
    image_file_id = config.get_welcome_image_file_id()
    delete_after = config.get_delete_after_seconds()

    for member in message.new_chat_members:
        if member.is_bot:
            continue

        display_name = member.full_name or member.first_name or "nuevo miembro"
        mention = f"[{display_name}](tg://user?id={member.id})"
        text = config.get_welcome_text().replace("{nombre}", mention)

        try:
            if image_file_id:
                sent = await context.bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=image_file_id,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            else:
                sent = await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            logger.info(f"[welcome] Sent welcome message to new member {member.id} ({display_name}); message_id={sent.message_id}")
        except TelegramError as e:
            logger.error(f"[welcome] Failed to send welcome message to {member.id}: {e}")
            continue

        if delete_after and delete_after > 0 and context.job_queue:
            context.job_queue.run_once(
                _delete_welcome_message,
                when=delete_after,
                data={"chat_id": GROUP_ID, "message_id": sent.message_id},
                name=f"welcome_delete_{sent.message_id}",
            )


async def _delete_welcome_message(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: deletes a welcome message after its configured delay."""
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
        logger.info(f"[welcome] Deleted welcome message {data['message_id']}")
    except TelegramError as e:
        logger.warning(f"[welcome] Could not delete welcome message {data['message_id']}: {e}")


def _build_welcome_menu_text(config: WelcomeConfigManager) -> str:
    status = "🟢 Activado" if config.is_enabled() else "🔴 Desactivado"
    image_status = "Configurada" if config.get_welcome_image_file_id() else "(sin imagen)"
    text_preview = config.get_welcome_text()
    if len(text_preview) > 300:
        text_preview = text_preview[:300] + "…"
    buttons_summary = "\n".join(
        f"  • {label}: {config.get_button_url(key) or '(no configurado)'}"
        for key, label in WELCOME_BUTTON_LABELS.items()
    )
    return (
        "👋 **Configuración de Bienvenida**\n\n"
        f"Estado: {status}\n"
        f"Imagen: {image_status}\n"
        f"Borrar después de: {config.get_delete_after_seconds()} segundos\n\n"
        f"Texto actual:\n{text_preview}\n\n"
        f"Botones:\n{buttons_summary}\n\n"
        "¿Qué deseas modificar? Cada cambio se guarda de inmediato."
    )


def _welcome_menu_keyboard(config: WelcomeConfigManager) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Desactivar bienvenida" if config.is_enabled() else "🟢 Activar bienvenida"
    keyboard = [
        [InlineKeyboardButton(toggle_label, callback_data="welcome_toggle")],
        [InlineKeyboardButton("📝 Cambiar Texto", callback_data="welcome_edit_text")],
        [InlineKeyboardButton("🖼 Cambiar Imagen", callback_data="welcome_edit_image")],
    ]
    for key, label in WELCOME_BUTTON_LABELS.items():
        keyboard.append([InlineKeyboardButton(f"🔗 {label}", callback_data=f"welcome_edit_button_{key}")])
    keyboard.append([InlineKeyboardButton("⏱ Cambiar tiempo de borrado", callback_data="welcome_edit_delete_seconds")])
    keyboard.append([InlineKeyboardButton("✅ Terminar", callback_data="welcome_done")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


async def welcome_config_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: admin opened '👋 Configurar Bienvenida' from the panel."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return ConversationHandler.END

    context.user_data.pop("welcome_button_key", None)
    config = WelcomeConfigManager()
    logger.info("[welcome_config] Admin opened welcome configuration menu.")
    await query.edit_message_text(
        _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
    )
    return WELCOME_MENU


async def welcome_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle taps on the welcome configuration menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return ConversationHandler.END

    data = query.data

    if data == "welcome_toggle":
        config = WelcomeConfigManager()
        config.set_enabled(not config.is_enabled())
        saved = config.save()
        logger.info(f"[welcome_config] Toggled enabled -> {config.is_enabled()} (save()={saved})")
        await query.edit_message_text(
            _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
        )
        return WELCOME_MENU

    if data == "welcome_edit_text":
        await query.edit_message_text(
            "📝 Envía el nuevo texto de bienvenida. Usa `{nombre}` donde quieras mencionar al nuevo miembro.",
            parse_mode="Markdown",
        )
        return WELCOME_TEXT_INPUT

    if data == "welcome_edit_image":
        await query.edit_message_text("🖼 Envía la nueva imagen de bienvenida (una foto).")
        return WELCOME_IMAGE_INPUT

    if data.startswith("welcome_edit_button_"):
        button_key = data[len("welcome_edit_button_"):]
        if button_key not in WELCOME_BUTTON_LABELS:
            return WELCOME_MENU
        context.user_data["welcome_button_key"] = button_key
        await query.edit_message_text(f"🔗 Envía la nueva URL para el botón «{WELCOME_BUTTON_LABELS[button_key]}»:")
        return WELCOME_BUTTON_INPUT

    if data == "welcome_edit_delete_seconds":
        await query.edit_message_text(
            "⏱ Envía cuántos segundos esperar antes de borrar el mensaje de bienvenida (número entero, 0 para no borrar):"
        )
        return WELCOME_DELETE_SECONDS_INPUT

    if data == "welcome_done":
        logger.info("[welcome_config] Admin finished editing welcome configuration.")
        await query.edit_message_text("✅ Configuración de bienvenida guardada.")
        context.user_data.pop("welcome_button_key", None)
        return ConversationHandler.END

    return WELCOME_MENU


async def welcome_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the new welcome text and save it immediately."""
    config = WelcomeConfigManager()
    config.set_welcome_text(update.message.text)
    saved = config.save()
    logger.info(f"[welcome_config] Welcome text updated (save()={saved}).")
    await update.message.reply_text(
        _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
    )
    return WELCOME_MENU


async def welcome_receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the new welcome image and save it immediately."""
    message = update.message
    if not message.photo:
        await message.reply_text("❌ Por favor envía una foto.")
        return WELCOME_IMAGE_INPUT

    file_id = message.photo[-1].file_id
    config = WelcomeConfigManager()
    config.set_welcome_image_file_id(file_id)
    saved = config.save()
    logger.info(f"[welcome_config] Welcome image updated (save()={saved}).")
    await message.reply_text(
        _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
    )
    return WELCOME_MENU


async def welcome_receive_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive a new URL for whichever button the admin picked, and save it immediately."""
    button_key = context.user_data.get("welcome_button_key")
    if not button_key:
        return WELCOME_MENU

    url = update.message.text.strip()
    config = WelcomeConfigManager()
    config.set_button_url(button_key, url)
    saved = config.save()
    logger.info(f"[welcome_config] Button '{button_key}' URL updated -> {url!r} (save()={saved}).")
    context.user_data.pop("welcome_button_key", None)
    await update.message.reply_text(
        _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
    )
    return WELCOME_MENU


async def welcome_receive_delete_seconds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the new auto-delete delay (in seconds) and save it immediately."""
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Envía un número entero de segundos (por ejemplo: 60).")
        return WELCOME_DELETE_SECONDS_INPUT

    seconds = int(text)
    config = WelcomeConfigManager()
    config.set_delete_after_seconds(seconds)
    saved = config.save()
    logger.info(f"[welcome_config] Delete-after-seconds updated -> {seconds} (save()={saved}).")
    await update.message.reply_text(
        _build_welcome_menu_text(config), reply_markup=_welcome_menu_keyboard(config), parse_mode="Markdown"
    )
    return WELCOME_MENU


# --- Phase 4: "✏️ Editar Promoción" flow ---
#
# Design: edit_select_promotion() is a new ConversationHandler entry point
# (triggered by the "edit_select_<id>" buttons already listed by the
# existing "edit_promo" branch in button_callback). It loads the promotion
# via PromotionsManager.get_by_id() and stores a *working copy* of its
# fields in context.user_data (edit_caption / edit_media /
# edit_admin_username). From there, EDIT_MENU lets the admin pick which
# field to change; each field has its own input state and always returns
# back to EDIT_MENU so multiple fields can be edited in one session. Only
# fields the admin actually changes differ from the working copy - anything
# untouched is saved back exactly as it was, satisfying "conservar los
# campos que no se quieran modificar". The actual save only happens once,
# in _apply_promotion_edit(), when the admin presses "✅ Guardar Cambios",
# and it uses PromotionsManager.get_by_id() / .update() exclusively.

def _build_edit_menu_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Render the current (in-progress) state of the promotion being edited."""
    promo_id = context.user_data.get("edit_promo_id", "?")
    caption = context.user_data.get("edit_caption", "")
    media = context.user_data.get("edit_media", [])
    admin_username = context.user_data.get("edit_admin_username", DEFAULT_ADMIN_USERNAME)
    caption_preview = caption if caption else "(vacío)"

    return (
        f"✏️ **Editando `{promo_id}`**\n\n"
        f"📝 Caption actual: {caption_preview}\n"
        f"🖼 Archivos: {len(media)} archivo(s)\n"
        f"👤 Admin: @{admin_username}\n\n"
        "¿Qué deseas modificar? Los campos que no toques se guardarán tal cual están."
    )


def _edit_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📝 Cambiar Caption", callback_data="edit_field_caption")],
            [InlineKeyboardButton("🖼 Reemplazar Archivos", callback_data="edit_field_media")],
            [InlineKeyboardButton("👤 Cambiar Usuario Admin", callback_data="edit_field_username")],
            [InlineKeyboardButton("✅ Guardar Cambios", callback_data="edit_done")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")],
        ]
    )


async def edit_select_promotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: admin picked a specific promotion from the edit list
    (callback_data="edit_select_<id>")."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return ConversationHandler.END

    promo_id = query.data.replace("edit_select_", "")
    manager = PromotionsManager()
    promo = manager.get_by_id(promo_id)

    if not promo:
        logger.warning(f"[panel_edit] Promotion {promo_id} not found when starting edit.")
        await query.edit_message_text(f"❌ La promoción `{promo_id}` ya no existe.", parse_mode="Markdown")
        return ConversationHandler.END

    # Working copy: nothing is written to promotions.json until the admin
    # explicitly presses "✅ Guardar Cambios".
    context.user_data.clear()
    context.user_data["edit_promo_id"] = promo_id
    context.user_data["edit_caption"] = promo.get("caption", "")
    context.user_data["edit_media"] = list(promo.get("media", []))
    context.user_data["edit_admin_username"] = promo.get("admin_username", DEFAULT_ADMIN_USERNAME)

    logger.info(f"[panel_edit] Admin started editing promotion {promo_id}.")

    await query.edit_message_text(
        _build_edit_menu_text(context), reply_markup=_edit_menu_keyboard(), parse_mode="Markdown"
    )
    return EDIT_MENU


async def edit_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle taps on the edit menu: choose a field to change, or save."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return ConversationHandler.END

    if query.data == "edit_field_caption":
        await query.edit_message_text("📝 Envía el nuevo texto (caption) para esta promoción:")
        return EDIT_CAPTION_INPUT

    if query.data == "edit_field_media":
        # Separate buffer for newly-received items, so if the admin backs
        # out without sending anything, the original media is untouched.
        context.user_data["edit_media_buffer"] = []
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Terminar de reemplazar archivos", callback_data="edit_media_done")]]
        )
        await query.edit_message_text(
            "🖼 Envía la(s) nueva(s) foto(s)/video(s) para esta promoción. Puedes enviar varias, una por una, "
            "para formar un álbum. Cuando termines, pulsa 'Terminar'.",
            reply_markup=keyboard,
        )
        return EDIT_MEDIA_INPUT

    if query.data == "edit_field_username":
        await query.edit_message_text("👤 Envía el nuevo usuario de Telegram del administrador (sin @):")
        return EDIT_USERNAME_INPUT

    if query.data == "edit_done":
        await _apply_promotion_edit(query, context)
        return ConversationHandler.END

    return EDIT_MENU


async def edit_receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the new caption text and return to the edit menu."""
    new_caption = update.message.text
    old_caption = context.user_data.get("edit_caption", "")
    context.user_data["edit_caption"] = new_caption

    logger.info(
        f"[panel_edit] Caption updated in-session for {context.user_data.get('edit_promo_id')}: "
        f"{old_caption!r} -> {new_caption!r}"
    )

    await update.message.reply_text(
        _build_edit_menu_text(context), reply_markup=_edit_menu_keyboard(), parse_mode="Markdown"
    )
    return EDIT_MENU


async def edit_receive_media_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive one photo/video while replacing a promotion's media. Stays in
    EDIT_MEDIA_INPUT so the admin can send several items to form an album."""
    message = update.message

    if message.photo:
        item = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        item = {"type": "video", "file_id": message.video.file_id}
    else:
        await message.reply_text("❌ Por favor envía una foto o un video.")
        return EDIT_MEDIA_INPUT

    buffer = context.user_data.setdefault("edit_media_buffer", [])
    buffer.append(item)

    logger.info(
        f"[panel_edit] Media item added to replacement buffer for "
        f"{context.user_data.get('edit_promo_id')}: {item}. Buffer size now {len(buffer)}."
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Terminar de reemplazar archivos", callback_data="edit_media_done")]]
    )
    await message.reply_text(
        f"✅ Archivo agregado ({len(buffer)} en total). Envía más o pulsa 'Terminar'.",
        reply_markup=keyboard,
    )
    return EDIT_MEDIA_INPUT


async def edit_media_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin finished sending replacement media. If nothing was sent, the
    original media is kept unchanged."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ No tienes permiso.")
        return ConversationHandler.END

    promo_id = context.user_data.get("edit_promo_id")
    buffer = context.user_data.get("edit_media_buffer", [])

    if buffer:
        context.user_data["edit_media"] = buffer
        logger.info(f"[panel_edit] Media replaced in-session for {promo_id}: {len(buffer)} new file(s).")
    else:
        logger.info(f"[panel_edit] No new media received for {promo_id}; keeping original media unchanged.")

    context.user_data.pop("edit_media_buffer", None)

    await query.edit_message_text(
        _build_edit_menu_text(context), reply_markup=_edit_menu_keyboard(), parse_mode="Markdown"
    )
    return EDIT_MENU


async def edit_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the new admin contact username and return to the edit menu."""
    new_username = update.message.text
    old_username = context.user_data.get("edit_admin_username", "")
    context.user_data["edit_admin_username"] = new_username

    logger.info(
        f"[panel_edit] Admin username updated in-session for {context.user_data.get('edit_promo_id')}: "
        f"{old_username!r} -> {new_username!r}"
    )

    await update.message.reply_text(
        _build_edit_menu_text(context), reply_markup=_edit_menu_keyboard(), parse_mode="Markdown"
    )
    return EDIT_MENU


async def _apply_promotion_edit(query, context: ContextTypes.DEFAULT_TYPE):
    """Persist the working copy in context.user_data back into promotions.json,
    using PromotionsManager's public API exclusively (get_by_id + update)."""
    promo_id = context.user_data.get("edit_promo_id")
    manager = PromotionsManager()
    original = manager.get_by_id(promo_id)

    if not original:
        logger.error(f"[panel_edit] Promotion {promo_id} not found at save time (may have been deleted meanwhile).")
        await query.edit_message_text(f"❌ La promoción `{promo_id}` ya no existe.", parse_mode="Markdown")
        context.user_data.clear()
        return

    new_caption = context.user_data.get("edit_caption", original.get("caption", ""))
    new_media = context.user_data.get("edit_media", original.get("media", []))
    new_username = context.user_data.get(
        "edit_admin_username", original.get("admin_username", DEFAULT_ADMIN_USERNAME)
    )

    changed_fields = []
    if new_caption != original.get("caption", ""):
        changed_fields.append("caption")
    if new_media != original.get("media", []):
        changed_fields.append("media")
    if new_username != original.get("admin_username", DEFAULT_ADMIN_USERNAME):
        changed_fields.append("admin_username")

    # Keep any other fields on the promotion untouched (dict copy + overwrite
    # only the three editable fields), consistent with the project's existing
    # promotion shape (id, caption, media, admin_username).
    updated_promo = dict(original)
    updated_promo["caption"] = new_caption
    updated_promo["media"] = new_media
    updated_promo["admin_username"] = new_username

    logger.info("[panel_edit] ========== SAVING EDIT ==========")
    logger.info(f"[panel_edit] Promotion edited: {promo_id}")
    logger.info(f"[panel_edit] Changed fields: {changed_fields if changed_fields else 'ninguno'}")

    success = manager.update(promo_id, updated_promo)

    logger.info(f"[panel_edit] manager.update() result: {success}")
    logger.info("[panel_edit] ========== EDIT END ==========")

    if success:
        fields_text = ", ".join(changed_fields) if changed_fields else "ninguno (sin cambios)"
        await query.edit_message_text(
            f"✅ Promoción `{promo_id}` actualizada correctamente.\nCampos modificados: {fields_text}",
            parse_mode="Markdown",
        )
    else:
        logger.error(f"[panel_edit] ❌ Failed to save edited promotion {promo_id}.")
        await query.edit_message_text(f"❌ Error al actualizar la promoción `{promo_id}`.", parse_mode="Markdown")

    context.user_data.clear()


START_WELCOME_TEXT = (
    "🚀 ¡Bienvenido a EC Promociones VIP! 👋\n\n"
    "🔥 Accede a nuestros grupos exclusivos con contenido actualizado todos los días.\n\n"
    "✨ ¿Qué obtendrás?\n\n"
    "✅ Acceso inmediato al VIP.\n"
    "✅ Contenido exclusivo y actualizado.\n"
    "✅ Compra rápida y segura.\n"
    "✅ Soporte cuando lo necesites.\n\n"
    "👇 Presiona el botón para conocer los planes y comenzar ahora."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    logger.info(f"Received /start from chat_id={update.effective_chat.id} type={update.effective_chat.type}")

    # Deep-link "/start venta" (el botón del canal) sigue abriendo el menú
    # de ventas directamente, sin pasar por este mensaje de bienvenida.
    from ventas.config import SALES_DEEP_LINK_PAYLOAD
    if context.args and context.args[0] == SALES_DEEP_LINK_PAYLOAD:
        from ventas.handlers import send_sales_welcome
        await send_sales_welcome(update, context)
        return

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👑 Quiero ser VIP", callback_data="start_enter_vip")]])
    await update.message.reply_text(START_WELCOME_TEXT, reply_markup=keyboard)


async def start_enter_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botón "👑 Quiero ser VIP" del mensaje de /start: abre exactamente el
    mismo flujo que /start venta, reutilizando send_sales_welcome() sin
    duplicar su lógica."""
    query = update.callback_query
    await query.answer()
    from ventas.handlers import send_sales_welcome
    await send_sales_welcome(update, context)


def _describe_channel_message(message) -> dict:
    """Extract loggable fields from a channel_post / edited_channel_post message.

    This is a pure helper (no I/O) so it can be reused by both the
    channel_post and edited_channel_post handlers without duplicating logic.
    """
    channel_id = message.chat_id
    message_id = message.message_id
    media_group_id = message.media_group_id
    caption = message.caption

    photo_file_id = message.photo[-1].file_id if message.photo else None
    video_file_id = message.video.file_id if message.video else None

    if message.photo:
        content_type = "photo"
    elif message.video:
        content_type = "video"
    elif message.document:
        content_type = "document"
    elif message.animation:
        content_type = "animation"
    elif message.text:
        content_type = "text"
    else:
        content_type = "other"

    return {
        "channel_id": channel_id,
        "message_id": message_id,
        "media_group_id": media_group_id,
        "caption": caption,
        "content_type": content_type,
        "photo_file_id": photo_file_id,
        "video_file_id": video_file_id,
    }


def _build_media_item(message) -> Optional[Dict]:
    """Build a single media item (dict with type + file_id) from a channel message.

    Only photo and video are supported, matching what publish_promotion()
    already knows how to send. Returns None if the message carries no
    supported media (e.g. plain text, document).
    """
    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id}
    if message.video:
        return {"type": "video", "file_id": message.video.file_id}
    return None


def _extract_promotion_caption(message) -> str:
    """Resolve the text to use as the promotion caption.

    Uses the media caption when present; falls back to the plain message
    text so that text-only channel posts (no photo/video) can also be
    captured as promotions, consistent with publish_promotion() supporting
    text-only promotions.
    """
    if message.caption:
        return message.caption
    if message.text:
        return message.text
    return ""


def _next_promotion_id(manager: PromotionsManager) -> str:
    """Generate the next sequential, collision-free promotion ID.

    Uses the same "promo_XXX" format already used throughout the project
    (admin panel, PromotionsManager, publish_promotion), so it stays fully
    compatible everywhere an ID is displayed or matched.

    Phase 3 integration fix: the original scheme elsewhere in the project
    (see add_username()) derives the next ID from len(existing) + 1. That
    works only while IDs stay perfectly contiguous. If a promotion is ever
    deleted via the admin panel's "🗑 Eliminar Promoción", the list becomes
    shorter than the highest ID already in use, and a length-based ID can
    collide with a promotion that still exists (e.g. deleting promo_003 out
    of promo_001..promo_006 leaves 5 promotions, so len+1 would produce
    "promo_006" again). A duplicate ID breaks get_by_id()/update()/delete(),
    which all match on the first promotion with that ID. To keep
    automatically-ingested promotions safe from this, this function instead
    looks at the highest numeric suffix actually in use and adds 1 to it.
    add_username() itself is intentionally left untouched, per Phase 3
    scope (no changes to the admin panel/conversations).
    """
    highest = 0
    for promo in manager.get_all():
        promo_id = str(promo.get("id", ""))
        if promo_id.startswith("promo_"):
            suffix = promo_id[len("promo_"):]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return f"promo_{str(highest + 1).zfill(3)}"


async def _notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Send a private Telegram message to the admin. Best-effort: a failure
    here (e.g. the admin never opened a DM with the bot, or blocked it)
    must never interrupt the automatic promotion save/edit it reports on.
    """
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"[channel_ingest] Could not send admin notification: {e}")


async def _notify_admin_new_promotion(context: ContextTypes.DEFAULT_TYPE, promo_id: str, caption: str, media: List[Dict]) -> None:
    """Phase 5: tell the admin a promotion was just created automatically
    from a channel post, so they know to review it without having to
    stumble on it in /panel."""
    caption_preview = caption.strip() if caption and caption.strip() else "(sin texto)"
    if len(caption_preview) > 120:
        caption_preview = caption_preview[:120] + "…"
    media_types = ", ".join(m.get("type", "?") for m in media) if media else "ninguno"

    text = (
        "🆕 *Nueva promoción creada automáticamente*\n\n"
        f"ID: `{promo_id}`\n"
        f"Caption: {caption_preview}\n"
        f"Archivos: {len(media)} ({media_types})\n\n"
        "Puedes revisarla o editarla con /panel."
    )
    await _notify_admin(context, text)


async def _notify_admin_promotion_updated(context: ContextTypes.DEFAULT_TYPE, promo_id: str, media_count: int) -> None:
    """Phase 5: tell the admin a promotion was updated automatically
    (a late-arriving album item was appended to it after the fact)."""
    text = (
        "✏️ *Promoción actualizada automáticamente*\n\n"
        f"ID: `{promo_id}`\n"
        "Llegó un archivo tardío de un álbum y se agregó a la promoción ya guardada.\n"
        f"Ahora tiene {media_count} archivo(s) en total."
    )
    await _notify_admin(context, text)


async def _notify_admin_error(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Phase 5: tell the admin an automatic save/edit failed, so a silent
    data-loss doesn't go unnoticed (mirrors the existing logger.error calls
    right before each of these are invoked)."""
    await _notify_admin(context, f"❌ {text}\n\nRevisa los logs del bot para más detalle.")


async def _save_new_promotion(
    caption: str, media: List[Dict], source_channel_id: int, context: ContextTypes.DEFAULT_TYPE
) -> Optional[str]:
    """Persist a new promotion built from a channel post using PromotionsManager.

    Uses the exact same storage format PromotionsManager already works with
    (id, caption, media, admin_username), so it stays fully compatible with
    publish_promotion(), the admin panel, and promotions.json.

    Returns the new promotion ID on success, or None if saving failed.
    """
    manager = PromotionsManager()
    promo_id = _next_promotion_id(manager)

    new_promo = {
        "id": promo_id,
        "caption": caption,
        "media": media,
        "admin_username": DEFAULT_ADMIN_USERNAME,
    }

    logger.info(
        f"[channel_ingest] Saving promotion {promo_id} from channel {source_channel_id} "
        f"with {len(media)} media file(s)"
    )

    if manager.add(new_promo):
        logger.info(f"[channel_ingest] ✅ Promotion {promo_id} saved successfully from channel post.")
        await _notify_admin_new_promotion(context, promo_id, caption, media)
        return promo_id

    logger.error(f"[channel_ingest] ❌ Failed to save promotion {promo_id} from channel post.")
    await _notify_admin_error(context, f"No se pudo guardar la promoción automática `{promo_id}`.")
    return None


def _prune_recently_finalized_groups() -> None:
    """Drop entries from recently_finalized_groups older than the TTL.

    Keeps this small in-memory dict from growing unbounded over a long
    bot uptime. Called opportunistically whenever a new album item comes
    in, so no separate scheduled job is needed for cleanup.
    """
    now = datetime.now()
    expired = [
        gid
        for gid, info in recently_finalized_groups.items()
        if (now - info["finalized_at"]).total_seconds() > RECENTLY_FINALIZED_TTL_SECONDS
    ]
    for gid in expired:
        recently_finalized_groups.pop(gid, None)


async def _append_media_to_existing_promotion(
    promo_id: str, media_item: Optional[Dict], caption: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Append a late-arriving album item to an already-saved promotion.

    Used when a media group finished its debounce window and was saved,
    but one more item for that same media_group_id shows up afterward
    (e.g. slow network). Appends to the existing promotion via
    PromotionsManager.update() rather than creating a second, duplicate
    promotion for the same album.
    """
    manager = PromotionsManager()
    promo = manager.get_by_id(promo_id)

    if not promo:
        logger.error(
            f"[channel_ingest] Could not find promotion {promo_id} to append a late album item to "
            f"(it may have been deleted from the admin panel)."
        )
        await _notify_admin_error(
            context, f"Llegó un archivo tardío para la promoción `{promo_id}`, pero ya no existe."
        )
        return

    if media_item:
        promo.setdefault("media", []).append(media_item)
    if caption and not promo.get("caption"):
        promo["caption"] = caption

    if manager.update(promo_id, promo):
        media_count = len(promo.get("media", []))
        logger.info(
            f"[channel_ingest] ✅ Late album item appended to promotion {promo_id}. "
            f"media_count={media_count}"
        )
        await _notify_admin_promotion_updated(context, promo_id, media_count)
    else:
        logger.error(f"[channel_ingest] ❌ Failed to append late album item to promotion {promo_id}.")
        await _notify_admin_error(
            context, f"No se pudo agregar un archivo tardío a la promoción `{promo_id}`."
        )


async def _finalize_media_group(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: runs once no new items have arrived for a media
    group for MEDIA_GROUP_DEBOUNCE_SECONDS, and saves everything buffered
    for that album as a single promotion."""
    media_group_id = context.job.data
    group = pending_media_groups.pop(media_group_id, None)

    if not group:
        logger.warning(
            f"[channel_ingest] Media group {media_group_id} had no buffered data at finalize time."
        )
        return

    media = group["media"]
    caption = group["caption"]
    channel_id = group["channel_id"]

    logger.info(
        f"[channel_ingest] Finalizing album. media_group_id={media_group_id} "
        f"channel_id={channel_id} media_count={len(media)}"
    )

    if not media and not caption.strip():
        logger.warning(
            f"[channel_ingest] Media group {media_group_id} has no usable caption or media, skipping save."
        )
        return

    promo_id = await _save_new_promotion(caption=caption, media=media, source_channel_id=channel_id, context=context)

    if promo_id:
        # Remember this group as finalized so a late-arriving item (network
        # delay pushed it past the debounce window) gets appended to this
        # same promotion instead of creating a duplicate one. See
        # _ingest_channel_post_as_promotion() and _prune_recently_finalized_groups().
        recently_finalized_groups[media_group_id] = {
            "promo_id": promo_id,
            "finalized_at": datetime.now(),
        }


async def _ingest_channel_post_as_promotion(message, context: ContextTypes.DEFAULT_TYPE):
    """Turn a channel_post message into a saved promotion (Phase 2).

    Single posts (no media_group_id) are saved immediately. Posts that are
    part of an album (shared media_group_id) are buffered in
    pending_media_groups and merged into a single promotion once no new
    items arrive for MEDIA_GROUP_DEBOUNCE_SECONDS (debounced via JobQueue),
    so an album never becomes multiple promotions.
    """
    media_group_id = message.media_group_id
    media_item = _build_media_item(message)
    caption = _extract_promotion_caption(message)
    channel_id = message.chat_id

    if media_group_id:
        logger.info(
            f"[channel_ingest] Detected ALBUM item. media_group_id={media_group_id} "
            f"message_id={message.message_id}"
        )

        _prune_recently_finalized_groups()

        # Integration fix (Phase 3): if this media_group_id was already
        # finalized into a promotion and this item is simply arriving late
        # (e.g. slow network pushed it past the debounce window), append it
        # to that existing promotion instead of starting a new buffer -
        # otherwise the same album would end up split into two promotions.
        late_info = recently_finalized_groups.get(media_group_id)
        if late_info and media_group_id not in pending_media_groups:
            logger.warning(
                f"[channel_ingest] Item for media_group_id={media_group_id} arrived after its album "
                f"was already saved as {late_info['promo_id']}. Appending instead of duplicating."
            )
            await _append_media_to_existing_promotion(late_info["promo_id"], media_item, caption, context)
            return

        group = pending_media_groups.setdefault(
            media_group_id,
            {"channel_id": channel_id, "caption": "", "media": []},
        )

        if media_item:
            group["media"].append(media_item)
        if caption and not group["caption"]:
            group["caption"] = caption

        if context.job_queue:
            # Reset the debounce timer: cancel any pending finalize job for
            # this group and schedule a new one, so we keep waiting until
            # the album stops sending items before saving it.
            job_name = f"media_group_finalize_{media_group_id}"
            for job in context.job_queue.get_jobs_by_name(job_name):
                job.schedule_removal()
            context.job_queue.run_once(
                _finalize_media_group,
                when=MEDIA_GROUP_DEBOUNCE_SECONDS,
                data=media_group_id,
                name=job_name,
            )
        else:
            logger.error(
                "[channel_ingest] JobQueue not available, cannot debounce media group. "
                "Saving immediately with items buffered so far."
            )
            pending_group = pending_media_groups.pop(media_group_id, None)
            if pending_group:
                await _save_new_promotion(
                    caption=pending_group["caption"],
                    media=pending_group["media"],
                    source_channel_id=pending_group["channel_id"],
                    context=context,
                )
    else:
        logger.info(f"[channel_ingest] Detected INDIVIDUAL post. message_id={message.message_id}")
        media = [media_item] if media_item else []

        if not media and not caption.strip():
            logger.warning(
                f"[channel_ingest] Channel post {message.message_id} has no usable caption or media, skipping save."
            )
            return

        await _save_new_promotion(caption=caption, media=media, source_channel_id=channel_id, context=context)


async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log new posts published directly in a channel (channel_post update)."""
    message = update.channel_post
    if message is None:
        return

    info = _describe_channel_message(message)
    logger.info("[channel_post] ========== NEW CHANNEL POST ==========")
    logger.info(f"[channel_post] Channel ID: {info['channel_id']}")
    logger.info(f"[channel_post] Message ID: {info['message_id']}")
    logger.info(f"[channel_post] media_group_id: {info['media_group_id']}")
    logger.info(f"[channel_post] Caption: {info['caption']}")
    logger.info(f"[channel_post] Content type: {info['content_type']}")
    logger.info(f"[channel_post] Photo file_id: {info['photo_file_id']}")
    logger.info(f"[channel_post] Video file_id: {info['video_file_id']}")
    logger.info("[channel_post] ========================================")

    # Phase 2: automatically save this new channel post as a promotion.
    await _ingest_channel_post_as_promotion(message, context)


async def handle_edited_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log edits to existing channel posts (edited_channel_post update)."""
    message = update.edited_channel_post
    if message is None:
        return

    info = _describe_channel_message(message)
    logger.info("[edited_channel_post] ========== EDITED CHANNEL POST ==========")
    logger.info(f"[edited_channel_post] Channel ID: {info['channel_id']}")
    logger.info(f"[edited_channel_post] Message ID: {info['message_id']}")
    logger.info(f"[edited_channel_post] media_group_id: {info['media_group_id']}")
    logger.info(f"[edited_channel_post] Caption: {info['caption']}")
    logger.info(f"[edited_channel_post] Content type: {info['content_type']}")
    logger.info(f"[edited_channel_post] Photo file_id: {info['photo_file_id']}")
    logger.info(f"[edited_channel_post] Video file_id: {info['video_file_id']}")
    logger.info("[edited_channel_post] ============================================")


async def post_init(application: Application):
    """Called after the application is initialized."""
    logger.info("Bot started. Scheduling promotions...")
    await schedule_promotions(application)


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
        
        logger.info(f"Promotion interval updated to {interval}s")
        await update.message.reply_text(f"✅ Intervalo actualizado correctamente a {interval}s ({in
