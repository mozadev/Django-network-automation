from zoneinfo import ZoneInfo
from dotenv import dotenv_values

config = dotenv_values(".env")

TZ = ZoneInfo(config["ZONE"])
PORT = config["PORT"]

