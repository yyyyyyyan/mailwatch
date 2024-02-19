from pathlib import Path
from subprocess import CalledProcessError

from watchdog.events import FileSystemEventHandler

from mailwatch.mailbox import MailWatchMailbox
from mailwatch.notification import NotificationHandler
from mailwatch.notification.exceptions import CommandNotFoundError
from mailwatch.notification.exceptions import IconNotFoundError


class NewMailEventHandler(FileSystemEventHandler):
    def __init__(self, logger, mailbox_path, *notification_options):
        self.logger = logger
        self.mailbox = MailWatchMailbox(mailbox_path, create=False)
        self.notification_handler = NotificationHandler(*notification_options)

    def _send_notification(self, **context):
        try:
            cmd = self.notification_handler.get_cmd(**context)
            self.logger.debug("Running command: '%s'", " ".join(cmd))
            self.notification_handler.send_notification(*cmd)
        except IconNotFoundError as err:
            self.logger.error("%s - no icon will be used", err)
            self.notification_handler.icon_fmt = None
            self._send_notification(**context)
        except CommandNotFoundError as err:
            self.logger.error(err)
        except CalledProcessError as err:
            self.logger.error(
                "Notification command returned an error and exited with status %(return_code)s: %(stderr)s",
                {"return_code": err.returncode, "stderr": err.stderr.decode("utf8")},
            )

    def on_created(self, event):
        what = "directory" if event.is_directory else "file"
        self.logger.info("Created %s: %s", what, event.src_path)
        context = {
            **self.mailbox.get_context(),
            **self.mailbox.get_message_context(Path(event.src_path).name),
        }
        self.logger.debug("Extra context for notification: %s", context)
        self._send_notification(**context)
