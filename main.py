import requests
import rich
import atexit
import re
from subprocess import Popen,CREATE_NEW_CONSOLE
from sys import executable
from rich.prompt import Prompt,IntPrompt
from rich import box
from rich.json import JSON
from rich.table import Table


BASE_URL="http://127.0.0.1:8000/"
# BASE_URL="http://clicapi.jprq.live/"
console=rich.console.Console()
TOKEN=""
def logout():
    if TOKEN!="":
        requests.post(BASE_URL+"auth/token/logout/",headers=HEADERS)

atexit.register(logout)


def getErrors(json):
    errors=""
    for error in json.values():
        if type(error)==list:
            for list_error in error:
                errors+=f"\n{list_error}\n"
        else:
            errors+=f"\n{error}\n"
    return errors

while True:
    console.print("Please select one of the options below : \n1-login\n2-register\n")
    inp=IntPrompt.ask("Your choice ",choices=["1","2"],default=1,show_default=False,show_choices=False)
    username=Prompt.ask("Please enter your username ")
    password=Prompt.ask("Please enter your password ")
    if inp==1:
        res = requests.post(BASE_URL+"auth/token/login/",json={
            "username":username,
            "password":password
        })
        if res.ok:
            TOKEN=res.json()['auth_token']
            HEADERS={"Authorization": f"Token {TOKEN}"}
            console.print(f"Logged in as {username}",style='green')
            break
        else:
            console.print(getErrors(res.json()),style='red')
    elif inp==2:
        res = requests.post(BASE_URL+"auth/users/",json={
            "username":username,
            "password":password
        })
        if res.ok:
            console.print(f"User {username} created.",style='green')
        else:
            console.print(getErrors(res.json()),style='red')


while True:
    console.print("Please select one of the options below : \n1-Friends and friend requests\n2-Invites\n3-Uploads\n4-Rooms\n0-Exit\n")
    inp=IntPrompt.ask("Your choice ",choices=["1","2","3","4","5","0"],show_choices=False)
    if inp==1:
        while True:
            console.print("Please select one of the options below : \n1-Friends\n2-Friend requests sent\n3-Friend requests received\n4-Send friend request\n5-Info\n0-Back\n")
            inp=IntPrompt.ask("Your choice ",choices=["1","2","3","4","5","0"],show_choices=False)
            if inp==1:
                res=requests.get(BASE_URL+"auth/users/me/",headers=HEADERS).json()['friends']
                for user in res:
                    if user['is_online']==True:
                        style="green"
                        in_room=f" | {user['currently_in'][0]['id']} {user['currently_in'][0]['name']}" if user['currently_in']!=[] else ''
                    else:
                        style="red"
                        in_room=""
                    console.print(f"\n{user['username']} | {user['id']}{in_room}\n",style=style)
            elif inp==2:
                res=requests.get(BASE_URL+"frequests/?mode=sent",headers=HEADERS).json()
                for frequest in res:
                    console.print(f"\nTo {frequest['receiver']['username']}\n")
            elif inp==3:
                matcher=re.compile(r"(?P<command>accept|decline) (?P<id>[0-9]+)")
                while True:
                    res=requests.get(BASE_URL+"frequests/?mode=received",headers=HEADERS).json()
                    for frequest in res:
                        console.print(f"\nFrom {frequest['sender']['username']} | Id : {frequest['id']}\n")
                    while True:
                        inp=Prompt.ask("Type accept/decline 'id' to accept or decline a friend request or type 0 to go back ")
                        if inp=="0":
                            break
                        else:
                            command = matcher.match(inp)
                            if command is not None:
                                res=requests.post(BASE_URL+f"frequests/{command.groupdict()['id']}/",json={"mode":command.groupdict()['command']},headers=HEADERS)
                                if res.ok:
                                    console.print("Friend request accepted!",style="green")
                                else:
                                    console.print(getErrors(res.json()),style="red")
                            else:
                                console.print("Invalid command!",style="red")
                    break
            elif inp==4:
                inp=IntPrompt.ask("Id of the user you want to send a friend request to ")
                res=requests.post(BASE_URL+"frequests/",json={"receiver":inp},headers=HEADERS)
                if res.ok:
                    console.print("Friend request sent!",style='green')
                else:
                    console.print(getErrors(res.json()),style='red')
            elif inp==5:
                console.print(f"Your id is {str(requests.get(BASE_URL+'auth/users/me/',headers=HEADERS).json()['id'])}",style='cyan')
            elif inp==0:
                break
    elif inp==2:
        go_back=False
        matcher=re.compile(r"join ((code (?P<code>[a-z0-9-]+))|(id (?P<rid>[0-9]+)))(?P<password> \w+)?")
        while not go_back:
            res=requests.get(BASE_URL+'auth/users/me/',headers=HEADERS)
            table=Table(title=f"Invited Rooms",caption="Type '0' to go back or \"join code/id 'code'/'id' 'password'\" to join a room.",box=box.ASCII2,show_lines=True)
            table.add_column("Id",justify="center",no_wrap=True,style="cyan")
            table.add_column("Name",justify="center",no_wrap=False,style="bright_yellow")
            table.add_column("Has Password",justify="center",no_wrap=True,style="green")
            table.add_column("Members/Limit",justify="center",no_wrap=True,style="magenta")
            table.add_column("Creator",justify="center",no_wrap=False,style="red")
            table.add_column("Invite member/admin",justify="center",no_wrap=True,style="white")
            table.add_column("Upload member/admin",justify="center",no_wrap=True,style="white")
            table.add_column("Code",justify="center",no_wrap=True,style="orange1")
            for room in res.json()['invited_to']:
                table.add_row(str(room["id"]),room["name"],str(room['has_password']),f"{str(room['member_count'])}/{str(room['limit'])}",room["creator"]["username"],f"{room['can_invite']}/{room['can_admins_invite']}",f"{room['can_upload']}/{room['can_admins_upload']}",room["code"])
            console.print(table)
            while True:
                inp=Prompt.ask("Command ")
                if inp=="0":
                    go_back=True
                    break
                command=matcher.match(inp)
                if command is None:
                    console.print("Invalid command!",style="red")
                else:
                    cmd_dir=command.groupdict()
                    if cmd_dir["rid"] is not None:
                        res=requests.get(BASE_URL+f"rooms/{cmd_dir['rid']}/",headers=HEADERS)
                        password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                        if res.ok:
                            Popen([executable,"room.py",res.json()["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
                        else:
                            console.print(getErrors(res.json()),style="red")
                    else:
                        password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                        Popen([executable,"room.py",cmd_dir["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
    elif inp==3:
        matcher=re.compile(r"delete (?P<id>[0-9]+)")
        while True:
            res=requests.get(BASE_URL+"uploads/?mode=user",headers=HEADERS).json()
            table=Table(title=f"Your Uploads",box=box.ASCII2,show_lines=True)
            table.add_column("Id",justify="center",no_wrap=True,style="cyan")
            table.add_column("File",justify="center",no_wrap=True,style="bright_yellow")
            table.add_column("Download name",justify="center",no_wrap=True,style="green")
            table.add_column("Caption",justify="center",no_wrap=True,style="magenta")
            table.add_column("Room Id",justify="center",no_wrap=True,style="red")
            table.add_column("Room Name",justify="center",no_wrap=True,style="orange1")
            table.add_column("Room Creator",justify="center",no_wrap=True,style="bright_green")
            for upload in res:
                table.add_row(str(upload['id']),upload['file'],upload['dname'],upload['caption'],str(upload['room']['id']),upload['room']['name'],upload['room']['creator']['username'])
            console.print(table)
            while True:
                inp=Prompt.ask("Type '0' to go back or \"delete 'id'\" to delete an upload ")
                if inp=="0":
                    break
                else:
                    command = matcher.match(inp)
                    if command is not None:
                        res=requests.delete(BASE_URL+f"uploads/{command.groupdict()['id']}/",headers=HEADERS)
                        if res.ok:
                            console.print("Upload deleted!",style="green")
                        else:
                            console.print(getErrors(res.json()),style="red")
                    else:
                        console.print("Invalid command!",style="red")
            break
    elif inp==4:
        while True:
            console.print("Please select one of the options below : \n1-Create a room\n2-Show/join rooms\n3-Your rooms\n4-Rooms that you are an admin\n5-Rooms that you are banned from\n6-Get room info\n0-Back\n")
            inp=IntPrompt.ask("Your choice ",choices=["1","2","3","4","5","6","0"],show_choices=False)
            if inp==1:
                name=Prompt.ask("Name ")
                limit=IntPrompt.ask("Limit ")
                welcome_text=Prompt.ask("Welcome message ")
                password=Prompt.ask("Password ")
                is_private=Prompt.ask("Private",choices=["y","n"],default="n")
                can_invite = Prompt.ask("Allow inviting",choices=["y","n"],default="y")
                can_admins_invite = Prompt.ask("Allow admins inviting",choices=["y","n"],default="y")
                can_upload = Prompt.ask("Allow uploading",choices=["y","n"],default="y")
                can_admins_upload = Prompt.ask("Allow admins uploading",choices=["y","n"],default="y")
                has_password=True if password!="" else False
                res = requests.post(BASE_URL+"rooms/",json={
                    "name":name,
                    "limit":limit,
                    "welcome_text":welcome_text,
                    "has_password":has_password,
                    "password":password,
                    "is_private":is_private,
                    "can_invite":can_invite,
                    "can_admins_invite":can_admins_invite,
                    "can_upload":can_upload,
                    "can_admins_upload":can_admins_upload
                },headers=HEADERS)
                
                if res.ok:
                    console.print(JSON(res.text))
                    console.print("Room created",style="green")
                else:
                    console.print(getErrors(res.json()),style='red')
            elif inp==2:
                go_back=False
                matcher=re.compile(r"((?P<page>page)|(?P<join>join)) (?(page)(?P<pid>[0-9]+)|((code (?P<code>[a-z0-9-]+)|id (?P<rid>[0-9]+))( (?P<password>\w+))?))")
                page="1"
                while not go_back:
                    res=requests.get(BASE_URL+f"rooms/?page={page}",headers=HEADERS)
                    if res.ok:
                            table=Table(title=f"Page {page} Rooms",caption="Type '0' to go back, \"page 'x'\" to go to a page or \"join code/id 'code'/'id' 'password'\" to join a room.",box=box.ASCII2,show_lines=True)
                            table.add_column("Id",justify="center",no_wrap=True,style="cyan")
                            table.add_column("Name",justify="center",no_wrap=False,style="bright_yellow")
                            table.add_column("Has Password",justify="center",no_wrap=True,style="green")
                            table.add_column("Members/Limit",justify="center",no_wrap=True,style="magenta")
                            table.add_column("Creator",justify="center",no_wrap=False,style="red")
                            table.add_column("Invite member/admin",justify="center",no_wrap=True,style="white")
                            table.add_column("Upload member/admin",justify="center",no_wrap=True,style="white")
                            table.add_column("Code",justify="center",no_wrap=True,style="orange1")
                            for room in res.json()["results"]:
                                table.add_row(str(room["id"]),room["name"],str(room['has_password']),f"{str(room['member_count'])}/{str(room['limit'])}",room["creator"]["username"],f"{room['can_invite']}/{room['can_admins_invite']}",f"{room['can_upload']}/{room['can_admins_upload']}",room["code"])
                            console.print(table)
                    else:
                        console.print(getErrors(res.json()),style='red')
                    while True:
                        inp=Prompt.ask("Command ")
                        if inp=="0":
                            go_back=True
                            break
                        command=matcher.match(inp)
                        if command is None:
                            console.print("Invalid command!",style="red")
                        else:
                            cmd_dir=command.groupdict()
                            if cmd_dir["page"] is not None:
                                page=cmd_dir["pid"]
                                break
                            elif cmd_dir["join"] is not None:
                                if cmd_dir["rid"] is not None:
                                    res=requests.get(BASE_URL+f"rooms/{cmd_dir['rid']}/",headers=HEADERS)
                                    password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                    if res.ok:
                                        Popen([executable,"room.py",res.json()["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
                                    else:
                                        console.print(getErrors(res.json()),style="red")
                                else:
                                    password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                    Popen([executable,"room.py",cmd_dir["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
            elif inp==3:
                go_back=False
                matcher=re.compile(r"join ((code (?P<code>[a-z0-9-]+))|(id (?P<rid>[0-9]+)))(?P<password> \w+)?")
                while not go_back:
                    res=requests.get(BASE_URL+f"auth/users/me/",headers=HEADERS)
                    table=Table(title=f"Your Rooms",caption="Type '0' to go back or \"join code/id 'code'/'id' 'password'\" to join a room.",box=box.ASCII2,show_lines=True)
                    table.add_column("Id",justify="center",no_wrap=True,style="cyan")
                    table.add_column("Name",justify="center",no_wrap=False,style="bright_yellow")
                    table.add_column("Has Password",justify="center",no_wrap=True,style="green")
                    table.add_column("Members/Limit",justify="center",no_wrap=True,style="magenta")
                    table.add_column("Creator",justify="center",no_wrap=False,style="red")
                    table.add_column("Is Private",justify="center",no_wrap=True)
                    table.add_column("Invite member/admin",justify="center",no_wrap=True,style="white")
                    table.add_column("Upload member/admin",justify="center",no_wrap=True,style="white")
                    table.add_column("Code",justify="center",no_wrap=True,style="orange1")
                    for room in res.json()["creator_of"]:
                        table.add_row(str(room["id"]),room["name"],str(room['has_password']),f"{str(room['member_count'])}/{str(room['limit'])}",room["creator"]["username"],str(room['is_private']),f"{room['can_invite']}/{room['can_admins_invite']}",f"{room['can_upload']}/{room['can_admins_upload']}",room["code"])
                    console.print(table)
                    while True:
                        inp=Prompt.ask("Command ")
                        if inp=="0":
                            go_back=True
                            break
                        command=matcher.match(inp)
                        if command is None:
                            console.print("Invalid command!",style="red")
                        else:
                            cmd_dir=command.groupdict()
                            if cmd_dir["rid"] is not None:
                                res=requests.get(BASE_URL+f"rooms/{cmd_dir['rid']}/",headers=HEADERS)
                                password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                if res.ok:
                                    Popen([executable,"room.py",res.json()["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
                                else:
                                        console.print(getErrors(res.json()),style="red")
                            else:
                                password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                Popen([executable,"room.py",cmd_dir["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
            elif inp==4:
                go_back=False
                matcher=re.compile(r"join ((code (?P<code>[a-z0-9-]+))|(id (?P<rid>[0-9]+)))(?P<password> \w+)?")
                while not go_back:
                    res=requests.get(BASE_URL+f"auth/users/me/",headers=HEADERS)
                    table=Table(title=f"Rooms with admin authority",caption="Type '0' to go back or \"join code/id 'code'/'id' 'password'\" to join a room.",box=box.ASCII2,show_lines=True)
                    table.add_column("Id",justify="center",no_wrap=True,style="cyan")
                    table.add_column("Name",justify="center",no_wrap=False,style="bright_yellow")
                    table.add_column("Has Password",justify="center",no_wrap=True,style="green")
                    table.add_column("Members/Limit",justify="center",no_wrap=True,style="magenta")
                    table.add_column("Creator",justify="center",no_wrap=False,style="red")
                    table.add_column("Is Private",justify="center",no_wrap=True)
                    table.add_column("Invite member/admin",justify="center",no_wrap=True,style="white")
                    table.add_column("Upload member/admin",justify="center",no_wrap=True,style="white")
                    table.add_column("Code",justify="center",no_wrap=True,style="orange1")
                    for room in res.json()["admin_of"]:
                        table.add_row(str(room["id"]),room["name"],str(room['has_password']),f"{str(room['member_count'])}/{str(room['limit'])}",room["creator"]["username"],str(room['is_private']),f"{room['can_invite']}/{room['can_admins_invite']}",f"{room['can_upload']}/{room['can_admins_upload']}",room["code"])
                    console.print(table)
                    while True:
                        inp=Prompt.ask("Command ")
                        if inp=="0":
                            go_back=True
                            break
                        command=matcher.match(inp)
                        if command is None:
                            console.print("Invalid command!",style="red")
                        else:
                            cmd_dir=command.groupdict()
                            if cmd_dir["rid"] is not None:
                                res=requests.get(BASE_URL+f"rooms/{cmd_dir['rid']}/",headers=HEADERS)
                                password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                if res.ok:
                                    Popen([executable,"room.py",res.json()["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
                                else:
                                        console.print(getErrors(res.json()),style="red")
                            else:
                                password=cmd_dir["password"] if cmd_dir["password"] is not None else ""
                                Popen([executable,"room.py",cmd_dir["code"],TOKEN,password,username],creationflags=CREATE_NEW_CONSOLE)
            elif inp==5:
                res=requests.get(BASE_URL+f"auth/users/me/",headers=HEADERS)
                table=Table(title=f"Rooms that you're banned from",box=box.ASCII2,show_lines=True)
                table.add_column("Id",justify="center",no_wrap=True,style="cyan")
                table.add_column("Name",justify="center",no_wrap=False,style="bright_yellow")
                table.add_column("Creator",justify="center",no_wrap=False,style="red")
                for room in res.json()["banned_from"]:
                    table.add_row(str(room["id"]),room["name"],room["creator"]["username"])
                console.print(table)
            elif inp==6:
                while True:
                    inp=IntPrompt.ask("Id of the room or 0 to go back ")
                    if inp!=0:
                        res=requests.get(BASE_URL+f"rooms/{inp}/",headers=HEADERS)
                        if res.ok:
                            console.print_json(res.text)
                        else:
                            console.print(getErrors(res.json()),style='red')
                    else:
                        break
            elif inp==0:
                break
    elif inp==0:
        exit()
