class ContextVar:
    SEPARATOR = ":"

    def __init__(self, ctx_str):
        try:
            self.key, self.value = ctx_str.split(self.SEPARATOR, 1)
        except ValueError as err:
            raise ValueError(
                f"{ctx_str} is not a valid context variable (not in key{self.SEPARATOR}value format)"
            ) from err
