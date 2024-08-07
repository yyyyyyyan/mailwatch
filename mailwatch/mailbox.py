from datetime import datetime
from email.header import decode_header
from mailbox import Maildir
from pathlib import Path


class MailWatchMailbox(Maildir):
    def __init__(self, dirname, **kwargs):
        self.name = Path(dirname).name
        super().__init__(dirname, **kwargs)

    def get_context(self):
        new_count = unread_count = read_count = 0
        for message in self:
            if message.get_subdir() == "new":
                new_count += 1
            if "S" in message.get_flags():
                read_count += 1
            else:
                unread_count += 1
        return {
            "name": self.name,
            "path": self._path,
            "new_count": new_count,
            "unread_count": unread_count,
            "read_count": read_count,
            "total_count": unread_count + read_count,
        }

    def get_message_context(self, filename):
        key = filename.split(self.colon)[0]
        message = self.get_message(key)
        context = {
            "delivery_date": datetime.fromtimestamp(message.get_date()),
            "headers": {},
        }
        for header_key, header_value in message.items():
            header_decoded, header_charset = decode_header(header_value)[0]
            if header_charset is not None:
                header_decoded = header_decoded.decode(header_charset)
            context["headers"][header_key] = header_decoded
        return context
