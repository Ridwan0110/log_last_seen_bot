"""
A simple bot that logs the last seen status of a specific WhatsApp user.
It subscribes to presence updates for the target user and prints their online/offline status in real-time.
"""

# Imports
import time
import traceback
import redu_logger, redu_config_manager, redu_build_manager
from neonize.client import NewClient
from neonize.events import ConnectedEv, PresenceEv
from neonize.utils import build_jid
from neonize.utils.enum import Presence
from pathlib import Path

__version__ = "1.0.0"

# Initialize Pathlib Paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE_PATH = BASE_DIR / "config.yaml"
BUILD_FILE_PATH = BASE_DIR / "BUILD"
for path in (CONFIG_FILE_PATH, BUILD_FILE_PATH):
    if not path.exists():
        path.touch()

# Initialize logger
local_log_file_name = "log_last_seen_bot.log"
local_log_path = str(Path(BASE_DIR / "logs"))

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
client = NewClient("session.db")


def get_target_number():
    logger.info("Retrieving target number from config...")
    return str(config_manager.get_value("target"))


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
            logger.info(f"[{sender_str}] is now ONLINE", True)
        else:
            logger.info(f"[{sender_str}] is now OFFLINE", True)

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
