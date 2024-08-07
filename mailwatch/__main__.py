import logging
import re
import sys
from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
from enum import IntEnum
from pathlib import Path
from time import sleep

from watchdog.observers import Observer

from mailwatch.events import NewMailEventHandler
from mailwatch.logging import ColorFormatter
from mailwatch.logging import LOG_LEVELS
from mailwatch.notification import ContextVar
from mailwatch.notification.context import Context
from mailwatch.notification.context import ContextFile


class ExitCodes(IntEnum):
    FILE_NOT_FOUND = 2
    NOT_A_DIRECTORY = 20


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Send notification on new maildir mail",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("account")
    mailbox_group = parser.add_argument_group("Mailbox Options")
    mailbox_group.add_argument(
        "-m",
        "--mailbox",
        default=[],
        action="append",
        type=re.escape,
        help="Mailbox names",
    )
    mailbox_group.add_argument(
        "--mailbox-regex",
        "--mr",
        default=[],
        action="append",
        help="Mailbox name regex patterns",
    )
    mailbox_group.add_argument(
        "--mailbox-exclude",
        "--mex",
        default=[],
        action="append",
        type=re.escape,
        help="Mailbox names to exclude",
    )
    mailbox_group.add_argument(
        "--mailbox-exclude-regex",
        "--mexr",
        default=["Sent", "Spam", "Drafts", "Trash"],
        action="append",
        help="Mailbox name regex patterns to exclude",
    )
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
    notify_send_group.add_argument(
        "--add",
        "--additional-context",
        action="append",
        default=[],
        type=ContextVar,
        dest="additional_context",
        help=f"Additional context in the format key{ContextVar.SEPARATOR}value",
    )
    notify_send_group.add_argument(
        "--addf",
        "--additional-context-file",
        action="append",
        default=[],
        type=ContextFile,
        dest="additional_context_files",
        help=f"Load additional context from ini/json/toml config file in the format key{ContextFile.SEPARATOR}path",
    )

    args = parser.parse_args()

    log_level = LOG_LEVELS.get(args.log_level, logging.INFO)
    logger = logging.getLogger("mailwatch")
    logger.setLevel(log_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(ColorFormatter())
    logger.addHandler(stream_handler)

    mail_path = args.mail_path / args.account
    if not mail_path.is_dir():
        logger.critical("'%s' is not a valid directory", mail_path)
        sys.exit(ExitCodes.NOT_A_DIRECTORY)
    mail_path_escaped = re.escape(str(mail_path))
    mailbox_regexes = [
        f"{mail_path_escaped}/{mailbox}/new/"
        for mailboxes in [args.mailbox, args.mailbox_regex]
        for mailbox in mailboxes
    ]
    if not mailbox_regexes:
        mailbox_regexes.append(f"{mail_path_escaped}/[^/]+/new/")
    mailbox_exclude_regexes = [
        f"{mail_path_escaped}/{mailbox}/"
        for mailboxes in [args.mailbox_exclude, args.mailbox_exclude_regex]
        for mailbox in mailboxes
    ]

    new_mail_event_handler = NewMailEventHandler(
        mailbox_regexes,
        mailbox_exclude_regexes,
        logger,
        args.notification_command,
        args.notification_summary,
        args.notification_body,
        args.notification_urgency,
        args.notification_duration,
        args.notification_icon,
    )

    default_context = Context(account=args.account)
    for context_file in args.additional_context_files:
        try:
            default_context[context_file.key] = Context.from_file(context_file.value)
        except (ValueError, FileNotFoundError) as err:  # noqa: PERF203
            logger.error(err)
    for context_variable in args.additional_context:
        default_context[context_variable.key] = context_variable.value
    new_mail_event_handler.notification_handler.set_default_context(**default_context)
    logger.debug("Default context for notifications: %s", default_context)

    observer = Observer()
    observer.schedule(new_mail_event_handler, mail_path, recursive=True)
    observer.start()
    logger.info("Mailbox regexes '%s'...", mailbox_regexes)
    logger.info("Mailbox exclude regexes '%s'...", mailbox_exclude_regexes)
    logger.info("Watching for new files at '%s'...", mail_path)
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logger.critical("SIGINT detected, exiting...")
        observer.stop()
    observer.join()
