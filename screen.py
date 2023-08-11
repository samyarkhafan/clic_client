import rich
import shared_memory_dict
from sys import argv
import time
from rich.console import Console
import os
console=rich.console.Console()

def show_exception_and_exit(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Press key to exit.")
    sys.exit(-1)

import sys
sys.excepthook = show_exception_and_exit

unique=argv[1]

smd=shared_memory_dict.SharedMemoryDict(unique,8192)
while True:
    time.sleep(0.2)
    if smd["changed"]==True:
        if smd['msg']['type']=='error':
            console.print(smd['msg']['text'],style='red')
        elif smd['msg']['type']=='room.join':
            if smd['msg']['text']['welcome']!='':
                console.rule('[bold]WELCOME[/bold]')
                console.print(smd['msg']['text']['welcome'],style='green',justify='center')
                console.rule()
        elif smd['msg']['type']=='room.message':
            console.print(smd['msg']['text'])
        elif smd['msg']['type']=='room.sys':
            console.print(smd['msg']['text'],style='cyan')
        elif smd['msg']['type']=='client_error':
            console.print(smd['msg']['text'],style='red')
        elif smd['msg']['type']=='client_ok':
            console.print(smd['msg']['text'],style='green')
        elif smd['msg']['type']=='client_info':
            console.print(smd['msg']['text'],style='cyan')
        elif smd['msg']['type']=='client_list':
            if type(smd['msg']['text'])==list:
                for msg in smd['msg']['text']:
                    console.print(msg,style='cyan')
            else:
                console.print(smd['msg']['text'])
        elif smd['msg']['type']=='client_title':
            os.system(f"{smd['msg']['text']}")
        smd["changed"]=False