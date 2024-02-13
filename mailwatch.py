import logging
import subprocess
import sys
from argparse import ArgumentParser
from mailbox import Maildir
from pathlib import Path

from watchdog.events import FileSystemEventHandler

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class NewMailEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        mailbox_path,
        notification_command,
        notification_summary,
        notification_body,
        notification_urgency,
        notification_duration,
        notification_icon,
    ):
        if not mailbox_path.is_dir():
            raise NotADirectoryError(f"{mailbox_path} is not a valid directory")
        self.mailbox = Maildir(mailbox_path, create=False)
        self.notification_command = notification_command
        self.notification_summary = notification_summary
        self.notification_body = notification_body
        self.notification_urgency = notification_urgency
        self.notification_duration = notification_duration
        self.notification_icon = notification_icon
        self.logger = logging.getLogger("mailwatch")

    def _get_default_context(self):
        new_count = unread_count = read_count = 0
        for message in self.mailbox:
            if message.get_subdir() == "new":
                new_count += 1
            if "S" in message.get_flags():
                read_count += 1
            else:
                unread_count += 1
        return {
            "new_count": new_count,
            "unread_count": unread_count,
            "read_count": read_count,
            "total_count": unread_count + read_count,
        }

    def _send_notification(self, **context):
        initial_cmd = self.notification_command.format(**context)
        summary = self.notification_summary.format(**context)
        body = self.notification_body.format(**context)
        icon = Path(str(self.notification_icon).format(**context)).resolve()
        cmd = [
            *initial_cmd.split(),
            f"--urgency={self.notification_urgency}",
            f"--expire-time={self.notification_duration}",
        ]
        if icon.is_file():
            cmd.append(f"--icon={icon}")
        else:
            self.logger.error(f"{icon} is not a valid file - no icon will be used")
        cmd.extend(
            [
                summary,
                body,
            ]
        )

        self.logger.debug(f"Running command: '{' '.join(cmd)}'")
        try:
            proc = subprocess.run(cmd, capture_output=True)
            if proc.stderr:
                self.logger.error(
                    f"Notification command returned an error: {proc.stderr.decode('utf8')}"
                )
        except FileNotFoundError:
            self.logger.error(f"Notification command '{cmd[0]}' not found")

    def on_created(self, event):
        # message = self.mailbox.get_message(event.src_path.split(self.mailbox.colon)[0])
        context = self._get_default_context()
        self._send_notification(context)
        # TODO: add headers to context from/subject/ to? (decode)
        # TODO: add account to context


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
        default=Path(__file__).parent / "static/mail.png",
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
        if not mailbox_path.is_dir():
            raise NotADirectoryError(f"{mailbox_path} is not a valid directory")
        new_mail_event_handler = NewMailEventHandler(
            mailbox_path.parent,
            args.notification_command,
            args.notification_summary,
            args.notification_body,
            args.notification_urgency,
            args.notification_duration,
            args.notification_icon,
        )
    except NotADirectoryError as err:
        logger.critical(err)
        sys.exit(20)
