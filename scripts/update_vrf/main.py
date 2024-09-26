import os
from dotenv import load_dotenv
from utils import to_router
import sys

load_dotenv()


def main():
    """
    Datos de ingreso:
    ip_pe: 
    subinterace:
    vrf_old: 
    vrf_new:
    cliente: 
    asnumer:
    password: 
    """
    pe = sys.argv[1]
    sub_interface = sys.argv[2]
    vrf_new = int(sys.argv[3])
    vrf_old = int(sys.argv[4])
    cliente = sys.argv[5].upper()
    asnumber = sys.argv[6]
    password = sys.argv[7]

    result = to_router(pe, sub_interface, vrf_new, vrf_old, cliente, asnumber, password)
    print(result)
    return


if __name__ == "__main__":
    main()