import subprocess
from pathlib import Path


class IconNotFoundError(FileNotFoundError):
    pass


class CommandNotFoundError(FileNotFoundError):
    pass


class ContextVar:
    SEPARATOR = ":"

    def __init__(self, ctx_str):
        try:
            self.key, self.value = ctx_str.split(self.SEPARATOR, 1)
        except ValueError as err:
            raise ValueError(
                f"{ctx_str} is not a valid context variable (not in key{self.SEPARATOR}value format)"
            ) from err


class NotificationHandler:
    def __init__(self, cmd_fmt, summary_fmt, body_fmt, urgency, duration, icon_fmt):
        self.cmd_fmt = cmd_fmt
        self.summary_fmt = summary_fmt
        self.body_fmt = body_fmt
        self.urgency = urgency
        self.duration = duration
        self.icon_fmt = icon_fmt
        self._default_context = {}

    @property
    def default_context(self):
        return self._default_context

    def set_default_context(self, **context):
        self._default_context = context

    def add_default_context(self, **context):
        self._default_context.update(context)

    def get_cmd(self, **context):
        context = {**self.default_context, **context}
        cmd = [
            self.cmd_fmt.format(**context).split(),
            f"--urgency={self.urgency}",
            f"--expire-time={self.duration}",
        ]
        if self.icon_fmt is not None:
            icon = Path(self.icon_fmt.format(**context)).resolve()
            if not icon.is_file():
                raise FileNotFoundError(f"{icon} is not a valid file")
            cmd.append(f"--icon={icon}")
        cmd.extend(
            [
                self.summary_fmt.format(**context),
                self.body_fmt.format(**context),
            ]
        )
        return cmd

    def send_notification(self, *cmd, **context):
        if not cmd:
            cmd = self.get_cmd(**context)
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except FileNotFoundError as err:
            raise CommandNotFoundError(
                f"Notification command '{cmd[0]}' not found"
            ) from err
