import logging
import sys
from argparse import ArgumentParser
from enum import IntEnum
from pathlib import Path

from mailwatch.events import NewMailEventHandler
from mailwatch.logging import ColorFormatter
from mailwatch.logging import LOG_LEVELS


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
        default="New mail from {message.headers.from}",
        help="Notification summary",
    )
    notify_send_group.add_argument(
        "-b",
        "--notification-body",
        default="{mailbox.unread_count} unread emails in {account}",
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
        logger.critical(f"{mailbox_path} is not a valid directory")
        sys.exit(ExitCodes.NOT_A_DIRECTORY)

    new_mail_event_handler = NewMailEventHandler(
        mailbox_path.parent,
        args.notification_command,
        args.notification_summary,
        args.notification_body,
        args.notification_urgency,
        args.notification_duration,
        args.notification_icon,
    )
    new_mail_event_handler.notification_handler.add_default_context(
        account=args.account, mailbox_path=mailbox_path
    )
    # TODO: add offlineimap options to gather context
    # TODO: create observer and schedule event
