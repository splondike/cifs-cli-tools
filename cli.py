import os
import sys
import configparser
import urllib.parse
from smb.SMBConnection import SMBConnection


config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), "config.ini")
config.read(config_path)

username = config["general"]["username"]
password = config["general"]["password"]
smb_uri = urllib.parse.urlparse(config["general"]["smb_uri"])
server_ip = smb_uri.netloc
share_name = [i for i in smb_uri.path.split("/") if i != ""][0]

smb_conn = SMBConnection(username, password, "sync", "sync")
assert smb_conn.connect(server_ip, 139)

if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help"):
    print("Supported commands: ls, rm, push, pull")
    sys.exit(0)

command = sys.argv[1]

def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    step_unit = 1024.0

    for x in ["B", "K", "M", "G", "T"]:
        if num < step_unit:
            return "%.1f%s" % (num, x)
        num /= step_unit

if command == "ls":
    path = sys.argv[-1] if sys.argv[-1] not in ("ls", "-l") else "/"
    include_filesize = "-l" in sys.argv
    for file in smb_conn.listPath(share_name, path):
        if file.filename in (".", ".."):
            continue
        elif file.isDirectory:
            file_size = "0b " if include_filesize else ""
            print(f"{file_size}{file.filename}/")
        else:
            file_size = f"{convert_bytes(file.file_size)} " if include_filesize else ""
            print(f"{file_size}{file.filename}")
elif command == "pull":
    remote_path = sys.argv[2]
    if len(sys.argv) == 4:
        local_path = sys.argv[3]
    else:
        local_path = os.path.join(
            os.getcwd(),
            os.path.basename(remote_path)
        )

    with open(local_path, "wb") as fh:
        smb_conn.retrieveFile(share_name, remote_path, fh)
elif command == "push":
    local_path = sys.argv[2]
    remote_path = sys.argv[3]
    if remote_path.endswith("/"):
        remote_path += os.path.basename(local_path)

    with open(local_path, "rb") as fh:
        smb_conn.storeFile(share_name, remote_path, fh)
elif command == "rm":
    remote_path = sys.argv[2]
    if smb_conn.getAttributes(share_name, remote_path).isDirectory:
        smb_conn.deleteDirectory(share_name, remote_path)
    else:
        smb_conn.deleteFiles(share_name, remote_path)
else:
    print("Supported commands: ls, rm, push, pull")
    sys.exit(1)
