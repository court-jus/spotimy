from Queue import Queue
from threading import Thread
from spotipy.client import SpotifyException
import sys
import time


class SliceWorker(Thread):
    def __init__(self, queue_in, queue_out, func):
        Thread.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.func = func

    def run(self):
        while True:
            args, kwargs = self.queue_in.get()
            try:
                result = self.func(*args, **kwargs)
                self.queue_out.put(result)
            except:
                self.queue_in.put((args, kwargs))
            finally:
                self.queue_in.task_done()


def do_bunch(func, items_arg=None, items_kwarg=None, limit=100, args=None, kwargs=None):
    """
    Call a Spotipy method multiple times if needed by the size of the "list"
    argument.
    """
    result = []
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    if items_arg is None and items_kwarg is None:
        raise ValueError("items_arg or items_kwarg must be present")
    pre_args = []
    post_args = args[:]
    if items_arg:
        pre_args = args[:items_arg]
        items = args[items_arg]
        post_args = args[items_arg+1:]
        while items:
            sub_items = items[:limit]
            items = items[limit:]
            tmp_args = pre_args + [sub_items] + post_args
            done = False
            while not done:
                try:
                    sub_res = func(*tmp_args, **kwargs)
                    if not isinstance(sub_res, (list, tuple)):
                        sub_res = [sub_res]
                    result.extend(sub_res)
                except SpotifyException as e:
                    if e.http_status == 429:
                        # API rate limit exceeded
                        # Retry later
                        print("API rate limit exceeded, sleep")
                        time.sleep(0.3)
                    else:
                        raise
                else:
                    done = True
    else:
        items = kwargs.pop(items_kwarg)
        while items:
            sub_items = items[:limit]
            items = items[limit:]
            tmp_kwargs = kwargs.copy()
            tmp_kwargs.update({items_kwarg: sub_items})
            done = False
            while not done:
                try:
                    sub_res = func(*args, **tmp_kwargs)
                    if not isinstance(sub_res, (list, tuple)):
                        sub_res = [sub_res]
                    result.extend(sub_res)
                except SpotifyException as e:
                    if e.http_status == 429:
                        # API rate limit exceeded
                        # Retry later
                        print("API rate limit exceeded, sleep")
                        time.sleep(0.3)
                    else:
                        raise
                else:
                    done = True
    return result


def get_whole(func, *args, **kwargs):
    result = []

    # Get total and first pack of items
    limit, offset = 50, 0
    items = func(limit=limit, offset=0, *args, **kwargs)
    total = items["total"]
    result.extend(items["items"])
    if len(result) >= total:
        return result
    slices = range(len(result), total, limit)

    qin = Queue()
    qout = Queue()
    for x in range(8):
        worker = SliceWorker(qin, qout, func)
        worker.daemon = True
        worker.start()

    for slice in slices:
        nkw = kwargs.copy()
        nar = args[:]
        nkw.update({"limit": 50, "offset": slice})
        qin.put((nar, nkw))

    qin.join()
    while not qout.empty():
        subresult = qout.get()
        try:
            result.extend(subresult["items"])
        finally:
            qout.task_done()
    # sys.stdout.write(" CR\n")
    # sys.stdout.flush()
    return result

def get_album_tracks(sp, album):
    result = get_whole(sp.album_tracks, album["album"]["id"])
    return result

def get_user_albums(sp):
    result = get_whole(sp.current_user_saved_albums)
    return result

