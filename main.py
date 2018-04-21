#!/usr/bin/env python3

import logging
import os
import re
import sys
from configparser import ConfigParser

from telethon import TelegramClient, events
from telethon.tl.functions import channels
from telethon.tl.functions.messages import ImportChatInviteRequest

logging.basicConfig(format="%(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Config:
    def __init__(self, config_name):
        config_parser = ConfigParser()
        config_parser.read(config_name)

        self.api_id = config_parser.getint("telethon", "api_id")
        self.api_hash = config_parser.get("telethon", "api_hash")
        self.session_name = config_parser.get("telethon", "session_name",
                                              fallback="default")

        self.forwarder_channels = set(
            c.strip() for c in
            config_parser.get("forwarder", "channels",
                              fallback="").split(","))

        self.patterns = [
            p.strip() for p in config_parser.get("forwarder", "patterns",
                                                 fallback="").split(",")]

        self.recipient = config_parser.get("forwarder", "recipient",
                                           fallback="me").strip()

        self.downloader_channels = set(
            c.strip() for c in
            config_parser.get("downloader", "channels",
                              fallback="").split(","))

        self.download_directory = config_parser.get("downloader",
                                                    "download_directory",
                                                    fallback="./")
        if not self.download_directory.endswith("/"):
            self.download_directory += "/"

        self.download_audios = config_parser.getboolean(
            "downloader", "download_audios", fallback=True)
        self.download_documents = config_parser.getboolean(
            "downloader", "download_documents", fallback=True)
        self.download_gifs = config_parser.getboolean(
            "downloader", "download_gifs", fallback=True)
        self.download_photos = config_parser.getboolean(
            "downloader", "download_photos", fallback=True)
        self.download_stickers = config_parser.getboolean(
            "downloader", "download_stickers", fallback=True)
        self.download_videos = config_parser.getboolean(
            "downloader", "download_videos", fallback=True)
        self.download_video_notes = config_parser.getboolean(
            "downloader", "download_video_notes", fallback=True)
        self.download_voices = config_parser.getboolean(
            "downloader", "download_voices", fallback=True)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        config_file = "config.ini"
    elif len(sys.argv) == 2:
        config_file = sys.argv[1]
    else:
        sys.exit("Error: command line arguments are not valid.")

    config = Config(config_file)

    os.makedirs(config.download_directory, exist_ok=True)

    client = TelegramClient(config.session_name,
                            config.api_id, config.api_hash,
                            update_workers=4, spawn_read_thread=False)
    client.start()

    forwarder_channels = []

    for c_name in config.forwarder_channels:
        try:
            channel = client.get_input_entity(c_name)
        except ValueError as e:
            if 'Join the group' in str(e):
                invite = c_name.rsplit('/', 1)[-1]
                client(ImportChatInviteRequest(invite))
                channel = client.get_input_entity(c_name)
            else:
                raise

        forwarder_channels.append(channel)

    recipient = client.get_input_entity(config.recipient)

    downloader_channels = [client.get_input_entity(c)
                           for c in config.downloader_channels]

    if not forwarder_channels and downloader_channels:
        sys.exit("sys.exiting, there is no channel to watch.")

    if forwarder_channels:
        @client.on(events.NewMessage(incoming=True, chats=forwarder_channels))
        @client.on(events.MessageEdited(incoming=True,
                                        chats=forwarder_channels))
        def forwarder(event):
            logger.debug("Received a message from a channel in forwarder list")
            client(channels.ReadHistoryRequest(event.input_chat,
                                               event.message.id))
            logger.debug("Marked the message as read")
            for pattern in config.patterns:
                if re.search(pattern, event.raw_text, re.I) is not None:
                    logger.info("The message matches a pattern, forwarding it")
                    return event.forward_to(recipient)

    if downloader_channels:
        event_mapper = []
        if config.download_audios:
            event_mapper.append(('audio', 'Audio'))
        if config.download_gifs:
            event_mapper.append(('gif', 'GIF'))
        if config.download_photos:
            event_mapper.append(('photo', 'Photo'))
        if config.download_stickers:
            event_mapper.append(('sticker', 'Sticker'))
        if config.download_videos:
            event_mapper.append(('video', 'Video'))
        if config.download_video_notes:
            event_mapper.append(('video_note', 'Video note'))
        if config.download_voices:
            event_mapper.append(('voice', 'Voice'))
        if config.download_documents:
            event_mapper.append(('document', 'Document'))

        @client.on(events.NewMessage(incoming=True, chats=downloader_channels))
        def downloader(event):
            logger.debug("Received a message "
                         "from a channel in downloader list")
            client(channels.ReadHistoryRequest(event.input_chat,
                                               event.message.id))
            logger.debug("Marked the message as read")
            for key, name in event_mapper:
                if getattr(event, key):
                    location = client.download_media(event.message,
                                                     config.download_directory)
                    logger.info("{} downloaded to {}".format(name, location))

    print("Listening for new messages...")
    client.idle()
