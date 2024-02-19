import logging
import sys
from argparse import ArgumentParser
from enum import IntEnum
from pathlib import Path
from time import sleep

from watchdog.observers import Observer

from mailwatch.events import NewMailEventHandler
from mailwatch.logging import ColorFormatter
from mailwatch.logging import LOG_LEVELS
from mailwatch.notification import ContextVar


class ExitCodes(IntEnum):
    FILE_NOT_FOUND = 2
    NOT_A_DIRECTORY = 20


if __name__ == "__main__":
    parser = ArgumentParser(description="Send notification on new maildir mail")
    parser.add_argument("account")
    parser.add_argument("-m", "--mailbox", default="INBOX", help="Mailbox name")
    parser.add_argument(
        "-p",
        "--mail-path",
        default=Path.home() / "mail",
        type=Path,
        help="Path to mail folder",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level",
    )

    notify_send_group = parser.add_argument_group("notify-send Options")
    notify_send_group.add_argument(
        "-c",
        "--notification-command",
        default="/usr/bin/notify-send",
        help="Command to send notification",
    )
    notify_send_group.add_argument(
        "-s",
        "--notification-summary",
        default="New mail from {message__headers__from}",
        help="Notification summary",
    )
    notify_send_group.add_argument(
        "-b",
        "--notification-body",
        default="{mailbox__unread_count} unread emails in {account}",
        help="Notification body",
    )
    notify_send_group.add_argument(
        "-u",
        "--notification-urgency",
        default="normal",
        choices=["low", "normal", "critical"],
        help="Notification urgency",
    )
    notify_send_group.add_argument(
        "-t",
        "--notification-duration",
        default=10000,
        type=int,
        help="Notification duration in milliseconds",
    )
    notify_send_group.add_argument(
        "-i",
        "--notification-icon",
        type=Path,
        help="Notification icon",
    )
    notify_send_group.add_argument(
        "--default-notification-icon",
        action="store_const",
        const=Path(__file__).parent.parent / "static/mail.png",
        dest="notification_icon",
        help="Use default notification icon (this option overrides --notification-icon)",
    )
    notify_send_group.add_argument(
        "--add",
        "--additional-context",
        action="append",
        type=ContextVar,
        dest="additional_context",
        help=f"Additional context in the format key{ContextVar.SEPARATOR}value",
    )
    # TODO: --additional-context-file - load additional context from ini/json/toml file

    args = parser.parse_args()

    log_level = LOG_LEVELS.get(args.log_level, logging.INFO)
    logger = logging.getLogger("mailwatch")
    logger.setLevel(log_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(ColorFormatter())
    logger.addHandler(stream_handler)

    mailbox_path = args.mail_path / args.account / args.mailbox / "new"
    if not mailbox_path.is_dir():
        logger.critical("%s is not a valid directory", mailbox_path)
        sys.exit(ExitCodes.NOT_A_DIRECTORY)

    new_mail_event_handler = NewMailEventHandler(
        logger,
        mailbox_path.parent,
        args.notification_command,
        args.notification_summary,
        args.notification_body,
        args.notification_urgency,
        args.notification_duration,
        args.notification_icon,
    )
    default_context = {"account": args.account, "mailbox_path": mailbox_path}
    for context_variable in args.additional_context:
        default_context[context_variable.key] = context_variable.value
    logger.debug("Default context for notifications: %s", default_context)
    new_mail_event_handler.notification_handler.add_default_context(**default_context)
    observer = Observer()
    observer.schedule(new_mail_event_handler, mailbox_path)
    observer.start()
    logger.info("Watching for new files at %s...", mailbox_path)
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logger.critical("SIGINT detected, exiting...")
        observer.stop()
    observer.join()
