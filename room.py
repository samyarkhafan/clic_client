import httpx
import aioconsole
import asyncio
import rich
import websocket
import re
import json
import shared_memory_dict
from subprocess import Popen,CREATE_NEW_CONSOLE
from sys import executable,argv
from rich import box
from rich.console import Console
from rich.table import Table
from subprocess import Popen,CREATE_NEW_CONSOLE
from sys import executable
import traceback
import datetime
import sys
import aiofile
import os
from rich.prompt import Prompt

console=rich.console.Console()
BASE_URL="http://127.0.0.1:8000/"


def show_exception_and_exit(exc_type, exc_value, tb):
    
    # console.print("Something went wrong, check the screen",style='red')
    traceback.print_exception(exc_type, exc_value, tb)
    input()
    sys.exit(-1)


sys.excepthook = show_exception_and_exit


def getErrors(json):
    errors=""
    for error in json.values():
        if type(error)==list:
            for list_error in error:
                errors+=f"\n{list_error}\n"
        else:
            errors+=f"\n{error}\n"
    return errors

code=argv[1]
token=argv[2]
password=argv[3]
username=argv[4]
unique=str(datetime.datetime.now())
smd=shared_memory_dict.SharedMemoryDict(unique,8192)
ws=websocket.WebSocket()

smd['changed']=False
smd['msg']={'type':'','text':''}

HEADERS={"Authorization": f"Token {token}"}

if password!="":
    ws.connect(f"ws://127.0.0.1:8000/ws/{code}/?token={token}&password={password}")
    # ws.connect(f"ws://clicws.jprq.live:32833/ws/{code}/?token={token}&password={password}")
else:
    ws.connect(f"ws://127.0.0.1:8000/ws/{code}/?token={token}")
    # ws.connect(f"ws://clicws.jprq.live:32833/ws/{code}/?token={token}")

async def printScreen(type,text):
    while True:
        await asyncio.sleep(0.2)
        if smd['changed']==False:
            smd["msg"]={'type':type,'text':text}
            smd["changed"]=True
            break

async def upload(cmd_dict):
    global room
    try:
        f=await aiofile.async_open(cmd_dict['upath'],'rb')
    except:
        await printScreen("client_error","Invalid path, make sure to serround the path with double quotes \"\"")
    else:
        await printScreen("client_info",f"Uploading {os.path.basename(f.file.name)}")
        
        async with httpx.AsyncClient(timeout=None) as client:
            res=await client.post(BASE_URL+"uploads/",data={
                    "room":room['id'],
                    "dname":cmd_dict['dname'] if cmd_dict['dname'] is not None else '',
                    'caption':cmd_dict['caption'] if cmd_dict['caption'] is not None else '',
            },files={'file':(os.path.basename(f.file.name),await f.read())},headers=HEADERS)
            await f.close()
            res_json=res.json()
            if res.is_success:
                await printScreen("client_ok","File uploaded!")
                ws.send(json.dumps({
                    "type":"chat",
                    "text":f"Uploaded file : {res_json['file']} | With download name : {res_json['dname']}\n{res_json['caption']}"
                }))
            else:
                await printScreen("client_error",getErrors(res_json))

async def download(cmd_dict):
    global room
    fname=cmd_dict['fname']
    async with httpx.AsyncClient(timeout=None) as client:
        res=await client.get(BASE_URL+f"uploads/download/{room['name']}/{cmd_dict['dname2']}/",headers=HEADERS)
    if res.is_success:
        await printScreen("client_info",f"Downloading {cmd_dict['dname2']} as {fname}")
        data=await res.aread()
        f=await aiofile.async_open(fname,"wb")
        await f.write(data)
        await f.close()
        await printScreen("client_ok",f'File {fname} saved!')
    else:
        await printScreen("client_error","Couldn't get file")



async def monitor_ws():    
    first=True
    global room
    while True:
        res = await asyncio.get_event_loop().run_in_executor(None,ws.recv)
        res_json=json.loads(res)
        if first==True:
            first=False
            Popen([executable,"screen.py",unique],creationflags=CREATE_NEW_CONSOLE)
            await asyncio.sleep(1.0)
            await printScreen("client_info","type * or *help to show the commands!")
        if res_json['type']=='room.join':
            room = res_json['text']['room']
            title=f"title {room['name']} - {room['creator']['username']} - [ {room['member_count']} / {room['limit']} ]"
            os.system(title)
            await printScreen("client_title",title)
        if res_json['type']=='room.info':
            room = res_json['text']
            title=f"title {room['name']} - {room['creator']['username']} - [ {room['member_count']} / {room['limit']} ]"
            os.system(title)
            await printScreen("client_title",title)
        else:
            await printScreen(res_json['type'],res_json['text'])


    

async def monitor_console():
    global room
    matcher=re.compile(r"((?P<up>\*up)|(?P<down>\*dn)|\*(?P<command>ban|kick|invite|make_admin|remove_admin)|(?P<set>\*set)|(?P<info>\*info)|(?P<delete>\*delete)|(?P<help>\*help|\*))(?(up) \"(?P<upath>[^\"]+)\"(?P<dname> \w+)?( \"(?P<caption>[^\"]+)\")?|(?(down)( (?P<dname2>\S+) (?P<fname>.+))?|(?(command) (?P<username>.+)|(?(set) (?P<fields>[a-z_&]+) (?P<values>.+)|$))))")
    while True:
        os.system('cls')
        inp=await aioconsole.ainput(f"{username} : ")
        cmd=matcher.match(inp)
        if cmd is not None:
            cmd_dict=cmd.groupdict()
            if cmd_dict['up'] is not None:
                asyncio.create_task(upload(cmd_dict))
            elif cmd_dict['down'] is not None:
                if cmd_dict['dname2'] is None:
                    table=Table(title=f"{room['name']} Uploads",box=box.ASCII2,show_lines=True)
                    table.add_column("Id",justify="center",no_wrap=True,style="cyan")
                    table.add_column("Name",justify="center",no_wrap=True,style="bright_yellow")
                    table.add_column("Download Name",justify="center",no_wrap=True,style="bright_green")
                    table.add_column("Uploader",justify="center",no_wrap=True,style="magenta")
                    async with httpx.AsyncClient(timeout=None) as client:
                        res=await client.get(BASE_URL+f"uploads/?mode=room&room={room['id']}",headers=HEADERS)
                    for file in res.json():
                        table.add_row(str(file['id']),file['file'],file['dname'],file['uploader']['username'])
                    await printScreen("client_list",table)
                else:
                    asyncio.create_task(download(cmd_dict))
            elif cmd_dict['command'] is not None:
                ws.send(
                    json.dumps({
                        "type":cmd_dict['command'],
                        "text":cmd_dict['username']
                    })
                )
            elif cmd_dict['set'] is not None:
                data={}
                for field,value in zip(cmd_dict['fields'].split('&'),cmd_dict['values'].split('&')):
                    data[field]=value
                async with httpx.AsyncClient(timeout=None) as client:
                    res=await client.patch(BASE_URL+f"rooms/{room['id']}/",json=data,headers=HEADERS)
                if res.is_success:
                    await printScreen("client_ok",res.json())
                    ws.send(json.dumps(
                        {"type":"update"}
                    ))
                else:
                    await printScreen("client_error",getErrors(res.json()))
            elif cmd_dict['info'] is not None:
                id=f"Id : {room['id']}"
                creator=f"Creator : {room['creator']['username']}"
                tablea=Table(title=f"{room['name']} Admins",box=box.ASCII2,show_lines=True)
                tablea.add_column("Id",justify="center",no_wrap=True,style="cyan")
                tablea.add_column("Username",justify="center",no_wrap=True,style="bright_yellow")
                for member in room['admins']:
                    tablea.add_row(str(member['id']),member['username'])
                tablem=Table(title=f"{room['name']} Members",box=box.ASCII2,show_lines=True)
                tablem.add_column("Id",justify="center",no_wrap=True,style="cyan")
                tablem.add_column("Username",justify="center",no_wrap=True,style="bright_yellow")
                for member in room['members']:
                    tablem.add_row(str(member['id']),member['username'])
                tableb=Table(title=f"{room['name']} Bans",box=box.ASCII2,show_lines=True)
                tableb.add_column("Id",justify="center",no_wrap=True,style="cyan")
                tableb.add_column("Username",justify="center",no_wrap=True,style="bright_yellow")
                for member in room['bans']:
                    tableb.add_row(str(member['id']),member['username'])
                tablei=Table(title=f"{room['name']} Invites",box=box.ASCII2,show_lines=True)
                tablei.add_column("Id",justify="center",no_wrap=True,style="cyan")
                tablei.add_column("Username",justify="center",no_wrap=True,style="bright_yellow")
                for member in room['invites']:
                    tablei.add_row(str(member['id']),member['username'])
                name=f"Name : {room['name']}"
                count=f"Member count : {str(room['member_count'])}"
                limit=f"Limit : {str(room['limit'])}"
                welcome=f"Welcome text : {room['welcome_text']}"
                code=f"Code : {room['code']}"
                has_password = f"Has password : {str(room['has_password'])}"
                password = f"Password : {room['password']}"
                is_private = f"Is private : {str(room['is_private'])}"
                can_invite = f"Can invite : {str(room['can_invite'])}"
                can_admins_invite = f"Can admins invite : {str(room['can_admins_invite'])}"
                can_upload = f"Can upload : {str(room['can_upload'])}"
                can_admins_upload = f"Can admins upload : {str(room['can_admins_upload'])}"
                message=[id,creator,tablea,tablem,tableb,tablei,name,count,limit,welcome,code,has_password,password,is_private,can_invite,can_admins_invite,can_upload,can_admins_upload]
                await printScreen("client_list",message)  
            elif cmd_dict['delete'] is not None:
                inp=Prompt.ask("Type the name of the room to delete it ")
                if inp==room['name']:
                    ws.send(json.dumps({"type":"delete"}))
            elif cmd_dict['help'] is not None:
                message={
                    "show uploads":"*dn",
                    "download":"*dn 'dname' 'save_to'",
                    "upload":"*up 'path to file surrounded with double quotes' 'download name' 'caption surrounded in double quotes'",
                    "ban/kick/invite/make_admin/remove_admin":"*'command' 'username'",
                    "set settings":"*set 'fields seperateed by &' 'values seperated by &'",
                    "show settings/info":"*info",
                    "delete room":"*delete",
                    "show help":"*help/*"
                }
                await printScreen("client_list",message)
        else:
            if inp!='':
                ws.send(json.dumps({
                    "type":"chat",
                    "text":inp
                }))
            

async def main():
    await asyncio.gather(monitor_ws(),monitor_console())

if __name__=='__main__':
    asyncio.run(main())

