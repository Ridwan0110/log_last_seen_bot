"""
A simple bot that logs the last seen status of a specific WhatsApp user.
It subscribes to presence updates for the target user and prints their online/offline status in real-time.
"""
# Imports
import os
import time
import traceback
import requests
import redu_logger, redu_config_manager, redu_build_manager
from neonize.client import NewClient
from neonize.events import ConnectedEv, PresenceEv
from neonize.utils import build_jid
from neonize.utils.enum import Presence
from pathlib import Path

__version__ = "1.0.2"

# Initialize Pathlib Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE_PATH = DATA_DIR / "config.yaml"
BUILD_FILE_PATH = DATA_DIR / "BUILD"
SESSION_FILE_PATH = DATA_DIR / "session.db"

# Ensure `config.yaml` exists and is a YAML mapping so the config manager loads a dict
if not CONFIG_FILE_PATH.exists() or CONFIG_FILE_PATH.stat().st_size == 0:
    CONFIG_FILE_PATH.write_text("{}\n")

# Ensure BUILD file exists
if not BUILD_FILE_PATH.exists():
    BUILD_FILE_PATH.touch()


# Initialize logger
local_log_file_name = "log_last_seen_bot.log"
local_log_path = str(Path(DATA_DIR / "logs"))

logger = redu_logger.RemoteLogger(
    local_logging=True,
    remote_logging=False,
    is_main=True,
    local_log_file_name=local_log_file_name,
    local_log_path=local_log_path,
    local_multi_log=False
)

# Initialize config manager
config_manager = redu_config_manager.ConfigManager(CONFIG_FILE_PATH)
# Initialize build manager
enable_build_manager = True  # False on release
build_manager = redu_build_manager.BuildManager(enable_build=enable_build_manager, build_file=BUILD_FILE_PATH, )

# Initialize client
client = NewClient(str(SESSION_FILE_PATH))


def send_discord_webhook(content: str):
    webhook_url = config_manager.get_value("discord_webhook_url")
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        logger.info("Overriding Discord webhook URL with environment variable.")
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL variable not set. Skipping Discord webhook.", True)
        return

    try:
        response = requests.post(webhook_url, json={"content": content})
        if response.status_code == 204:
            logger.info("Successfully sent message to Discord webhook.")
        else:
            logger.error(f"Failed to send message to Discord webhook. Status code: {response.status_code}", True)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error sending message to Discord webhook: {e}\n{error_details}", True)


def prompt_for_target_number():
    while True:
        target_number = input("Enter the target WhatsApp number (without country code, e.g., 880xxxxxxxxxx): ").strip()
        if target_number and not target_number.startswith("+") and target_number.isdigit():
            config_manager.set_value("target_number", target_number, save=True)
            return target_number
        else:
            print("Invalid format. Please enter a valid phone number without country code (e.g., 880xxxxxxxxxx).")


def get_target_number():
    logger.info("Retrieving target number from config...")
    target_number = config_manager.get_value("target_number")
    if os.environ.get("TARGET_NUMBER"):
        logger.info("Overriding target number with environment variable.")
        target_number = os.environ.get("TARGET_NUMBER")
    if not target_number:
        target_number = prompt_for_target_number()
    return str(target_number)


@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    try:
        logger.info("Connected! Monitoring started...", True)

        target_jid = build_jid(get_target_number())

        # STEP 1: Mark BOT as Online
        client.send_presence(Presence.AVAILABLE)
        logger.info("Bot marked as AVAILABLE", True)

        # Step 2: Subscribe to presence updates for the target user
        client.subscribe_presence(target_jid)
        logger.info(f"Subscribed to presence updates for {target_jid}", True)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error during connection phase: {e}\n{error_details}", True)


@client.event(PresenceEv)
def on_presence(_: NewClient, ev: PresenceEv):
    try:
        logger.debug(f"LastSeen {ev.LastSeen}", True)

        # 1. Extract JID from the 'From' attribute
        sender_user = ev.From.User
        sender_server = ev.From.Server
        sender_str = f"{sender_user}@{sender_server}"

        # 2. Determine status
        # In this structure, 'Unavailable' is a boolean.
        # If Unavailable is True, they are offline. If False, they are online.
        is_offline = ev.Unavailable

        if not is_offline:
            msg = f"[{sender_str}] is now ONLINE"
            logger.info(msg, True)
            send_discord_webhook(msg)
        else:
            msg = f"[{sender_str}] is now OFFLINE"
            logger.info(msg, True)
            send_discord_webhook(msg)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error processing presence event: {e}\n{error_details}")


# Primary Function
def main():
    """Wrapper to keep the bot alive through critical crashes."""
    while True:
        try:
            logger.info("Attempting to connect to WhatsApp servers...", True)
            client.connect()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt detected. Exiting...", True)
            break
        except Exception as e:
            # Catches ANY unknown bug that causes the client to crash
            error_details = traceback.format_exc()
            logger.error(f"Unexpected Error: {e}\n{error_details}", True)

            logger.info("Trying again in 15 seconds...", True)
            time.sleep(15)  # Pause to avoid spamming connection attempts if internet is down


# Entry Point
if __name__ == '__main__':
    logger.info("Starting 'Log Last Seen Bot'...")
    build_manager.generate_build_version()

    main()
