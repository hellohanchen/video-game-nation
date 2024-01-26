from vgnlog.levels import LoggingLevel


class ChannelLogger:
    def __init__(self):
        self.logger = ""
        self.channel = None

    def init(self, logger, channel):
        self.logger = logger
        self.channel = channel

    async def log(self, level: LoggingLevel, msg):
        if self.channel is None:
            return

        if level == LoggingLevel.ERROR:
            message = f"🔴 [{self.logger}] "
        elif level == LoggingLevel.WARN:
            message = f"🟡 [{self.logger}] "
        else:
            message = f"🟢 [{self.logger}] "

        try:
            await self.channel.send(message + msg)
        except Exception as err:
            print(f"log error: {err}, message: {msg}")

    async def warn(self, msg):
        await self.log(LoggingLevel.WARN, msg)

    async def info(self, msg):
        await self.log(LoggingLevel.INFO, msg)

    async def error(self, msg):
        await self.log(LoggingLevel.ERROR, msg)


ADMIN_LOGGER = ChannelLogger()
