from subprocess import CalledProcessError

from watchdog.events import LoggingEventHandler

from mailwatch.mailbox import MailWatchMailbox
from mailwatch.notification import CommandNotFoundError
from mailwatch.notification import IconNotFoundError
from mailwatch.notification import NotificationHandler


class NewMailEventHandler(LoggingEventHandler):
    def __init__(self, logger, mailbox_path, *notification_options):
        self.mailbox = MailWatchMailbox(mailbox_path, create=False)
        self.notification_handler = NotificationHandler(*notification_options)
        super().__init__(logger)

    def _send_notification(self, **context):
        self.logger.debug(f"Context for notification: {context}")
        try:
            cmd = self.notification_handler.get_cmd(**context)
            self.logger.debug(f"Running command: '{' '.join(cmd)}'")
            self.notification_handler.send_notification(*cmd)
        except IconNotFoundError as err:
            self.logger.error(f"{err} - no icon will be used")
            self.notification_handler.icon_fmt = None
            self._send_notification(**context)
        except CommandNotFoundError as err:
            self.logger.error(err)
        except CalledProcessError as err:
            self.logger.error(
                f"Notification command returned an error and exited with status {err.returncode}: {err.stderr.decode('utf8')}"
            )

    def on_created(self, event):
        super().on_created(event)
        context = {
            **self.mailbox.get_context(),
            **self.mailbox.get_message_context(event.src_path),
        }
        self.logger.debug(f"Context for notification: {context}")
        self._send_notification(**context)
