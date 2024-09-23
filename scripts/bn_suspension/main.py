import os
from dotenv import load_dotenv
from utils import to_router
import sys

load_dotenv()


def main():
    pe = sys.argv[1]
    sub_interface = sys.argv[2]
    to_router(pe, sub_interface)
    return


if __name__ == "__main__":
    main()