from pathlib import Path
from subprocess import CalledProcessError

from watchdog.events import RegexMatchingEventHandler

from mailwatch.mailbox import MailWatchMailbox
from mailwatch.notification import NotificationHandler
from mailwatch.notification.exceptions import CommandNotFoundError
from mailwatch.notification.exceptions import IconNotFoundError


class NewMailEventHandler(RegexMatchingEventHandler):
    def __init__(
        self,
        regexes,
        ignore_regexes,
        logger,
        *notification_options,
    ):
        super().__init__(regexes, ignore_regexes, ignore_directories=True)
        self.logger = logger
        self.notification_handler = NotificationHandler(*notification_options)
        self.mailboxes = {}

    def _send_notification(self, **context):
        try:
            cmd = self.notification_handler.get_cmd(**context)
            self.logger.debug("Running command: '%s'", cmd)
            self.notification_handler.send_notification(*cmd)
        except KeyError as err:
            self.logger.error("Key not found in context: '%s'", err)
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

    def _on_new_mail(self, message_path):
        message_path = Path(message_path)
        mailbox_path = message_path.parent.parent
        mailbox_name = mailbox_path.name
        if mailbox_name not in self.mailboxes:
            self.mailboxes[mailbox_name] = MailWatchMailbox(mailbox_path, create=False)
        mailbox = self.mailboxes[mailbox_name]
        context = {
            "mailbox": mailbox.get_context(),
            "message": mailbox.get_message_context(message_path.name),
        }
        self.logger.debug("Extra context for notification: %s", context)
        self._send_notification(**context)

    def on_created(self, event):
        self.logger.info("New file: '%s'", event.src_path)
        self._on_new_mail(event.src_path)

    def on_moved(self, event):
        self.logger.info("Moved file: '%s' -> '%s'", event.src_path, event.dest_path)
        self._on_new_mail(event.dest_path)
