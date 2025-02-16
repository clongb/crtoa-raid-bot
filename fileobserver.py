import watchdog.events
import watchdog.observers
import time

class Handler(watchdog.events.PatternMatchingEventHandler):
    def __init__(self):
        watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=['log.txt'],
                                                             ignore_directories=True, case_sensitive=False)
    def on_modified(self, event):
        file = open("./osubot/log.txt", "r")
        lines = file.read().splitlines()
        last_line = lines[-1]
        temp = open("templog.txt", "w")
        temp.write(f"{last_line}\n")
        temp.close()

src_path = "./osubot/"
handler = Handler()
observer = watchdog.observers.Observer()

observer.schedule(handler, path=src_path, recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
except:
    observer.stop()
        
observer.join()