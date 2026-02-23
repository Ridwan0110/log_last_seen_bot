"""
A simple bot that logs the last seen status of a specific WhatsApp user.
It subscribes to presence updates for the target user and prints their online/offline status in real-time.
"""

# Imports
import redu_logger, redu_config_manager, redu_build_manager
from neonize.client import NewClient
from neonize.events import ConnectedEv, PresenceEv
from neonize.utils import build_jid
from neonize.utils.enum import Presence
from pathlib import Path

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
build_manager = redu_build_manager.BuildManager(enable_build=enable_build_manager, build_file=BUILD_FILE_PATH,)


# Initialize client
client = NewClient("session.db")


def get_target_number():
    return str(config_manager.get_value("target"))

@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    logger.info("Connected! Monitoring started...")

    # Replace this with your target JID
    target_jid = build_jid(get_target_number())

    # STEP 1: Mark your BOT as Online
    # Without this, WhatsApp won't send you anyone else's status
    client.send_presence(Presence.AVAILABLE)
    logger.info("Bot marked as AVAILABLE")

    # This is the "Subscription" command
    # It tells WhatsApp to send PresenceEv for this user to your script
    client.subscribe_presence(target_jid)
    logger.info(f"Subscribed to presence updates for {target_jid}")


@client.event(PresenceEv)
def on_presence(_: NewClient, ev: PresenceEv):
    try:
        logger.debug(f"LastSeen {ev.LastSeen}")

        # 1. Extract JID from the 'From' attribute
        sender_user = ev.From.User
        sender_server = ev.From.Server
        sender_str = f"{sender_user}@{sender_server}"

        # 2. Determine status
        # In this structure, 'Unavailable' is a boolean.
        # If Unavailable is True, they are offline. If False, they are online.
        is_offline = ev.Unavailable

        if not is_offline:
            logger.info(f"[{sender_str}] is now ONLINE")
        else:
            logger.info(f"[{sender_str}] is now OFFLINE")

    except Exception as e:
        logger.error(f"Error processing event: {e}")


# Start the client
if __name__ == '__main__':
    logger.info("Starting 'Log Last Seen Bot'...")
    build_manager.generate_build_version()
    client.connect()
