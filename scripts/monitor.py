#!/usr/bin/env python3
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import binhex_patched

filename_in = 'innocent.jpg.hqx'
filename_out = 'innocent.jpg'

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')
        binhex_patched.hexbin(filename_in, filename_out)


if __name__ == "__main__":

    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("in_file")
    p.add_argument("out_file")
    args = p.parse_args()

    filename_in  = args.in_file
    filename_out = args.out_file
    binhex_patched.hexbin(filename_in, filename_out)
    
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=filename_in, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
