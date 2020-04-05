from threading import Thread
from queue import Queue, Empty


class ASyncStreamReader:
    '''
    This class implement an async stream reader, useful when reading from stdout/stderr in subprocesses
    '''

    def __init__(self, stdstream):
        def threadrun(queue, stream):
            while True:
                row = stream.readline()
                if row:
                    queue.put(row)
                else:
                    return

        self.queue = Queue()
        self.readerthread = Thread(target=threadrun, args=(self.queue, stdstream))
        self.readerthread.daemon = True
        self.readerthread.start()

    def readline(self):
        try:
            return self.queue.get(False)
        except Empty:
            return None
