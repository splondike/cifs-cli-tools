import os
import configparser
import urllib.parse
from smb.SMBConnection import SMBConnection


config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), "config.ini")
config.read(config_path)

username = config["general"]["username"]
password = config["general"]["password"]
smb_uri = urllib.parse.urlparse(config["general"]["smb_uri"])
local_path = config["sync"]["local_path"]
server_ip = smb_uri.netloc
share_name = [i for i in smb_uri.path.split("/") if i != ""][0]

# Local files
local_files = {}
for (dirpath, _, filenames) in os.walk(local_path):
    local_files[dirpath[len(local_path):] + "/"] = -1
    for filename in filenames:
        full_path = os.path.join(dirpath, filename)
        rel_path = full_path[len(local_path):]
        local_files[rel_path] = os.stat(full_path).st_size

smb_conn = SMBConnection(username, password, "sync", "sync")
assert smb_conn.connect(server_ip, 139)

# Remote files
rem_dir_queue = ["/"]
remote_files = {"/": -1}
while len(rem_dir_queue) > 0:
    path = rem_dir_queue.pop()
    for file in smb_conn.listPath(share_name, path):
        if file.filename in (".", ".."):
            continue
        elif file.isDirectory:
            dirpath = f"{path}{file.filename}/"
            rem_dir_queue.append(dirpath)
            remote_files[dirpath] = -1
        else:
            filename = f"{path}{file.filename}"
            remote_files[filename] = file.file_size

# Remove local files deleted on share
for filename in sorted(local_files.keys(), key=lambda x: len(x), reverse=True):
    if filename not in remote_files:
        path = os.path.join(local_path, filename[1:])
        if filename.endswith("/"):
            os.rmdir(path)
        else:
            os.unlink(path)

# Copy down new and updated remote files
for filename, filesize in remote_files.items():
    do_copy = (filename not in local_files) or \
              local_files[filename] != filesize
    if do_copy:
        full_path = os.path.join(local_path, filename[1:])
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as fh:
            smb_conn.retrieveFile(share_name, filename, fh)
