import logging

from watchdog.events import FileSystemEventHandler

from mailwatch.mailbox import MailWatchMailbox
from mailwatch.notification import CommandNotFoundError
from mailwatch.notification import IconNotFoundError
from mailwatch.notification import NotificationHandler

logger = logging.getLogger("mailwatch")


# TODO: herdar de LoggingEventHandler e definir self.logger
class NewMailEventHandler(FileSystemEventHandler):
    def __init__(self, mailbox_path, *notification_options):
        self.mailbox = MailWatchMailbox(mailbox_path, create=False)
        self.notification_handler = NotificationHandler(*notification_options)

    def _send_notification(self, **context):
        logger.debug(f"Context for notification: {context}")
        try:
            self.notification_handler.send_notification(**context)
        except IconNotFoundError as err:
            logger.error(f"{err} - no icon will be used")
            self.notification_handler.icon_fmt = None
            self._send_notification(**context)
        except CommandNotFoundError as err:
            logger.error(err)

    def on_created(self, event):
        context = {
            **self.mailbox.get_context(),
            **self.mailbox.get_message_context(event.src_path),
        }
        logger.debug(f"Context for notification: {context}")
        self._send_notification(**context)
