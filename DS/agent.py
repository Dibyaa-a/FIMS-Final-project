import os
import sqlite3
import hashlib
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import json

print('''
 __          __  _         _ _         __  __             _ _             _                _____           _
 \ \        / / | |       (_) |       |  \/  |           (_) |           (_)              / ____|         | |
  \ \  /\  / /__| |__  ___ _| |_ ___  | \  / | ___  _ __  _| |_ ___  _ __ _ _ __   __ _  | (___  _   _ ___| |_ ___ _ __ ___
   \ \/  \/ / _ \ '_ \/ __| | __/ _ \ | |\/| |/ _ \| '_ \| | __/ _ \| '__| | '_ \ / _` |  \___ \| | | / __| __/ _ \ '_ ` _ \\
    \  /\  /  __/ |_) \__ \ | ||  __/ | |  | | (_) | | | | | || (_) | |  | | | | | (_| |  ____) | |_| \__ \ ||  __/ | | | | |
     \/  \/ \___|_.__/|___/_|\__\___| |_|  |_|\___/|_| |_|_|\__\___/|_|  |_|_| |_|\__, | |_____/ \__, |___/\__\___|_| |_| |_|
                                                                                   __/ |          __/ |
                                                                                  |___/          |___/
WMS v 1.0 | Developed by: Dibya Sharma''')
db_file = '/Users/DS/.wms/file_hashes.db'
slack_webhook_url = 'https://hooks.slack.com/services/'

def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def send_to_slack(message):
    payload = {'text': message}
    requests.post(slack_webhook_url, data=json.dumps(payload))


class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        if file_path.endswith('.db-journal'):
            return
        file_name = os.path.basename(file_path)
        file_hash = calculate_file_hash(file_path)

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT hash FROM file_hashes WHERE file_name = ?', (file_name,))
        row = cursor.fetchone()

        if row is None:
            cursor.execute('INSERT INTO file_hashes (file_name, hash) VALUES (?, ?)', (file_name, file_hash))
            send_to_slack(f'New file detected: {file_name} with hash {file_hash}')
        else:
            old_hash = row[0]
            if old_hash != file_hash:
                cursor.execute('UPDATE file_hashes SET hash = ? WHERE file_name = ?', (file_hash, file_name))
                send_to_slack(f'File modified: {file_name}. Old hash: {old_hash}, New hash: {file_hash}')
                print(f'File modified: {file_name}. Old hash: {old_hash}, New hash: {file_hash}')

        conn.commit()
        conn.close()


conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS file_hashes (file_name TEXT, hash TEXT)')
conn.commit()

for file_name in os.listdir('.'):
    if os.path.isfile(file_name):
        file_hash = calculate_file_hash(file_name)
        cursor.execute('INSERT OR IGNORE INTO file_hashes (file_name, hash) VALUES (?, ?)', (file_name, file_hash))
conn.commit()
conn.close()

event_handler = MyHandler()
observer = Observer()
observer.schedule(event_handler, path='.', recursive=False)
observer.start()

print("Listening for changes in files...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()