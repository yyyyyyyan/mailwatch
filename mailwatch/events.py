import logging
import subprocess
from datetime import datetime
from email.header import decode_header
from mailbox import Maildir
from pathlib import Path

from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("mailwatch")


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

    def _get_mailbox_context(self):
        new_count = unread_count = read_count = 0
        for message in self.mailbox:
            if message.get_subdir() == "new":
                new_count += 1
            if "S" in message.get_flags():
                read_count += 1
            else:
                unread_count += 1
        return {
            "mailbox.new_count": new_count,
            "mailbox.unread_count": unread_count,
            "mailbox.read_count": read_count,
            "mailbox.total_count": unread_count + read_count,
        }

    def _get_message_context(self, message_key):
        message = self.mailbox.get_message(message_key)
        context = {"message.delivery_date": datetime.fromtimestamp(message.get_date())}
        for header_key, header_value in message.items():
            header_decoded, header_charset = decode_header(header_value)
            if header_charset is not None:
                header_decoded = header_decoded.decode(header_charset)
            context[f"message.headers.{header_key.lower()}"] = header_decoded
        return context

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
            logger.error(f"{icon} is not a valid file - no icon will be used")
        cmd.extend(
            [
                summary,
                body,
            ]
        )

        logger.debug(f"Running command: '{' '.join(cmd)}'")
        try:
            proc = subprocess.run(cmd, capture_output=True)
            if proc.stderr:
                logger.error(
                    f"Notification command returned an error: {proc.stderr.decode('utf8')}"
                )
        except FileNotFoundError:
            logger.error(f"Notification command '{cmd[0]}' not found")

    def on_created(self, event):
        context = {
            **self._get_message_context(event.src_path.split(self.mailbox.colon)[0]),
            **self._get_mailbox_context(),
        }
        logger.debug(f"Context for notification: {context}")
        self._send_notification(**context)
        # TODO: add headers to context from/subject/ to? (decode)
        # TODO: add account to context
