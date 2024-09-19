import os
from dotenv import load_dotenv
from utils import to_router
import sys

load_dotenv()


def main():
    cid = sys.argv[1]
    to_router(cid)
    return


if __name__ == "__main__":
    main()