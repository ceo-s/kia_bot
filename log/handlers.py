import os
import pathlib
import threading
import requests
from dotenv import load_dotenv
from logging import Handler, LogRecord

load_dotenv(".env")

BOT_TOKEN = os.environ.get("LOGGING_BOT_TOKEN")
END_USERS = os.environ.get("LOGGING_END_USERS").split(",")


class ConsoleHandler(Handler):

    CRITICAL = '\033[91m\033[4m\033[1m'
    ERROR = '\033[91m'
    WARNING = '\033[93m'
    INFO = '\033[92m'
    DEBUG = '\033[95m'
    _END = '\033[0m'

    def __init__(self, ) -> None:
        super().__init__()

    def emit(self, record: LogRecord) -> None:
        message = self.format(record)
        color = getattr(self, record.levelname)
        print(color + message + self._END)


class FileHandler(Handler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def emit(self, record: LogRecord) -> None:
        message = self.format(record) + "\n"

        threading.Thread(
            target=self.file_append,
            args=(message,),
            name="fileLoggingThread"
        ).start()

    def file_append(self, message: str):
        dir = pathlib.Path(__file__).parent
        path = f"{dir}/{self.filename}"

        with open(path, "a") as file:
            file.write(message)


class TelegramHandler(Handler):
    def __init__(self, project_name: str) -> None:
        super().__init__()
        self.project_name = project_name

    def emit(self, record: LogRecord) -> None:
        if BOT_TOKEN is not None:
            message = self.format(record).replace("<", " ").replace(">", " ")
            message = f"<b>{self.project_name}:</b>\n{message}"

            threading.Thread(
                target=self.send_message,
                args=(message,),
                name="fileLoggingThread"
            ).start()

    def send_message(self, message: str):
        for user_id in END_USERS:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text={message}&parse_mode=HTML"
            resp = requests.get(url)
