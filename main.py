#!/usr/bin/env python3

import logging
import os
import re
import sys
from configparser import ConfigParser

from telethon import TelegramClient, events
from telethon.tl.functions import channels

logging.basicConfig(format="%(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if len(sys.argv) == 1:
    config_file = "config.ini"
elif len(sys.argv) == 2:
    config_file = sys.argv[1]
else:
    sys.exit("Error: command line arguments are not valid.")

config = ConfigParser()
config.read("config.ini")

api_id = config.getint("telethon", "api_id")
api_hash = config.get("telethon", "api_hash")
session_name = config.get("telethon", "session_name", fallback="default")

client = TelegramClient(session_name, api_id, api_hash,
                        update_workers=4, spawn_read_thread=False)
client.start()

forwarder_channels = [client.get_input_entity(c.strip())
                      for c in config.get("forwarder", "channels",
                                          fallback="").split(",")]
patterns = [p.strip() for p in config.get("forwarder", "patterns",
                                          fallback="").split(",")]
recipient = client.get_input_entity(config.get("forwarder", "recipient",
                                               fallback="me").strip())

downloader_channels = [client.get_input_entity(c.strip())
                       for c in config.get("downloader", "channels",
                                           fallback="").split(",")]
download_directory = config.get("downloader", "download_directory",
                                fallback="./")
if not download_directory.endswith("/"):
    download_directory += "/"
os.makedirs(download_directory, exist_ok=True)
download_audios = config.getboolean("downloader", "download_audios",
                                    fallback=True)
download_documents = config.getboolean("downloader", "download_documents",
                                       fallback=True)
download_gifs = config.getboolean("downloader", "download_gifs",
                                  fallback=True)
download_photos = config.getboolean("downloader", "download_photos",
                                    fallback=True)
download_stickers = config.getboolean("downloader", "download_stickers",
                                      fallback=True)
download_videos = config.getboolean("downloader", "download_videos",
                                    fallback=True)
download_video_notes = config.getboolean("downloader", "download_video_notes",
                                         fallback=True)
download_voices = config.getboolean("downloader", "download_voices",
                                    fallback=True)

if not forwarder_channels and downloader_channels:
    sys.exit("sys.exiting, there is no channel to watch.")

if forwarder_channels:
    @client.on(events.NewMessage(incoming=True, chats=forwarder_channels))
    @client.on(events.MessageEdited(incoming=True, chats=forwarder_channels))
    def forwarder(event):
        logger.debug("Received a message from a channel in forwarder list")
        client(channels.ReadHistoryRequest(event.input_chat, event.message.id))
        logger.debug("Marked the message as read")
        for pattern in patterns:
            if re.search(pattern, event.raw_text, re.I) is not None:
                logger.info("The message matches a pattern, forwarding it")
                return event.forward_to(recipient)

if downloader_channels:
    @client.on(events.NewMessage(incoming=True, chats=downloader_channels))
    def downloader(event):
        logger.debug("Received a message from a channel in downloader list")
        client(channels.ReadHistoryRequest(event.input_chat, event.message.id))
        logger.debug("Marked the message as read")
        if event.audio:
            if download_audios:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Audio downloaded to " + location)
        elif event.gif:
            if download_gifs:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("GIF downloaded to " + location)
        elif event.photo:
            if download_photos:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Photo downloaded to " + location)
        elif event.sticker:
            if download_stickers:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Sticker downloaded to " + location)
        elif event.video:
            if download_videos:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Video downloaded to " + location)
        elif event.video_note:
            if download_video_notes:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Video note downloaded to " + location)
        elif event.voice:
            if download_voices:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Voice downloaded to " + location)
        elif event.document:
            if download_documents:
                location = client.download_media(event.message,
                                                 download_directory)
                logger.info("Document downloaded to " + location)

print("Listening for new messages...")
client.idle()
