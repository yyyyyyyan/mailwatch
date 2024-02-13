import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from mailwatch.logging import ColorFormatter
from mailwatch.logging import LOG_LEVELS

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
        default="New mail from {from}",
        help="Notification summary",
    )
    notify_send_group.add_argument(
        "-b",
        "--notification-body",
        default="{unread_count} unread emails in {account}",
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
        default=Path(__file__).parent.parent / "static/mail.png",
        type=Path,
        help="Notification icon",
    )

    args = parser.parse_args()

    log_level = LOG_LEVELS.get(args.log_level, logging.INFO)
    logger = logging.getLogger("mailwatch")
    logger.setLevel(log_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(ColorFormatter())
    logger.addHandler(stream_handler)

    try:
        mailbox_path = args.mail_path / args.account / args.mailbox / "new"
        if not mailbox_path.exists():
            raise FileNotFoundError(f"{mailbox_path} does not exist")
        if not mailbox_path.is_dir():
            raise NotADirectoryError(f"{mailbox_path} is not a directory")
    except FileNotFoundError as err:
        logger.critical(err)
        sys.exit(2)
    except NotADirectoryError as err:
        logger.critical(err)
        sys.exit(20)
