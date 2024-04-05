"""
Wrapper around spotify API providing useful methods.
"""

import json
import os
import random
import sys
import time

import spotipy  # type: ignore
from spotipy import util

from .album import Album
from .utils import ms_to_human, percentile

ALBUMS_PAGE_HEADER = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>Albums</title>
        <style type="text/css">
            html {
                background-color: black;
                color: #eeefed;
                font-family: sans-serif;
            }
            body {
                margin: 0;
            }
            a {
                color: inherit;
                text-decoration: none;
            }
            .main-container {
                display: block;
                height: 100%;
                width: 100%;
            }
            .albums-container {
                display: flex;
                flex-flow: wrap;
                justify-content: space-around;
                height: 100vh;
                align-items: center;
            }
            .album-card-container {
                aspect-ratio: 9/16;
                height: 50vh;
                overflow: hidden;
                border: 1px solid #323232;
                box-sizing: border-box;
                padding: 0;
                margin: 0;
                flex: 1 0 19%;
            }
            .album-card {
                padding: 0;
                height: 100%;
                background-position: center;
                background-size: cover;
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
            }
            .album-card .album-details {
                display: block;
                background-color: black;
                height: 25%;
                overflow: hidden;
                text-align: center;
            }
            .album-card .album-details .album-title {
                margin: 2px;
                font-size: 1.2em;
            }
            .album-card .album-details .album-artists {
                margin: 1px;
                font-size: 1em;
            }
            .album-card .album-details .album-meta {
                margin: 0px;
                font-size: 0.8em;
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="albums-container">
"""
ALBUMS_PAGE_FOOTER = """
            </div>
        </div>
    </body>
</html>
"""


class Spotimy:
    """
    Wrapper around spotify API.
    """

    def __init__(self, config):
        self.config = config
        self.get_sp_client()

    def get_sp_client(self):
        """
        Get an instance of spotipy client.
        """
        scope = (
            "user-library-read playlist-modify-private "
            "playlist-modify-public user-library-modify "
            "playlist-read-private "
        )
        token_params = self.config["token"]

        self.username = token_params.pop("username")
        token = util.prompt_for_user_token(self.username, scope, **token_params)

        if token:
            self.sp = spotipy.Spotify(auth=token)
        else:
            print(f"Can't get token for {self.username}")
            sys.exit()

    def get_all_my_playlists(self):
        """
        Get a list of user's playlists.
        """
        result = []
        playlists = self.sp.current_user_playlists()
        while playlists:
            result.extend(playlists["items"])
            if not playlists["next"]:
                break
            playlists = self.sp.next(playlists)
        return result

    def add_my_plist_tracks_to_library(self):
        """
        Add all the tracks in user's playlists to their library.
        """
        save_playlists = self.config["sp"]
        print("Adding all tracks in playlists to user's library.")
        for plist in self.get_all_my_playlists():
            if plist["name"] in save_playlists:
                self.add_playlist_tracks_to_library(plist)

    def add_playlist_tracks_to_library(self, playlist):
        """
        Add all tracks in this playlist to user's library.
        """
        print(f"Adding tracks from playlist '{playlist['name']}' to user library")
        tracks = self.get_playlist_tracks(playlist)
        while len(tracks) > 48:
            subtracks = tracks[:48]
            tracks = tracks[48:]
            contained = self.sp.current_user_saved_tracks_contains(tracks=subtracks)
            contained = zip(subtracks, contained)
            subtracks = [trackid for trackid, already in contained if not already]
            if subtracks:
                self.sp.current_user_saved_tracks_add(tracks=subtracks)
        if tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=tracks)
            contained = zip(tracks, contained)
            tracks = [trackid for trackid, already in contained if not already]
            if tracks:
                self.sp.current_user_saved_tracks_add(tracks=tracks)

    def get_playlist_by_name(self, plist_name):
        """
        Find a playlist by its name.
        """
        for plist in self.get_all_my_playlists():
            if plist["name"] == plist_name:
                return plist

    def get_playlist_tracks(self, playlist, titles=False, username=None, full=False):
        """
        Return a list of tracks in a playlist.
        """
        if not playlist:
            return []
        if username is None:
            username = self.username
        result = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        while len(result) < biglimit and (total is None or len(result) < total):
            sub = self.sp.user_playlist_tracks(
                username, playlist["id"], limit=limit, offset=offset
            )
            result.extend(sub["items"])
            total = sub["total"]
            offset += limit

        if full:
            return result
        field = "name" if titles else "id"
        return [t["track"][field] for t in result]

    def clear_playlist(self, playlist):
        """
        Empty a playlist.
        """
        print(f"Clearing playlist '{playlist}'")
        playlist = self.get_playlist_by_name(playlist)
        tracks = self.get_playlist_tracks(playlist)
        if len(tracks) < 100:
            self.sp.user_playlist_remove_all_occurrences_of_tracks(
                self.username, playlist["id"], tracks
            )
        else:
            while tracks:
                sub_tracks = tracks[:100]
                tracks = tracks[100:]
                self.sp.user_playlist_remove_all_occurrences_of_tracks(
                    self.username, playlist["id"], sub_tracks
                )

    def get_album_tracks(self, album, titles=False):
        """
        Get a list of tracks in an album.
        """
        if not album:
            return []
        result = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        album_id = album["album"]["id"]
        while len(result) < biglimit and (total is None or len(result) < total):
            sub = self.sp.album_tracks(album_id, limit=limit, offset=offset)
            result.extend(sub["items"])
            total = sub["total"]
            offset += limit
        field = "name" if titles else "id"
        return map(lambda t: t[field], result)

    def get_user_albums(self):
        """
        Get a list of the user's albums.
        """
        print("Loading user albums")
        albums = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        while len(albums) < biglimit and (total is None or len(albums) < total):
            subalbums = self.sp.current_user_saved_albums(limit=limit, offset=offset)
            albums.extend(subalbums["items"])
            total = subalbums["total"]
            offset += limit
        return albums

    def add_library_to_sorting_plist(self, clear=True):
        """
        Find unsorted tracks in user's library and add them to the sorting playlist.

        Unsorted tracks are tracks that are not in any of the user's playlists nor in
        any of their favorited albums.
        """
        needs_sorting_playlist = self.config["nsp"]
        sort_playlists = self.config["sp"]
        print("Finding user tracks that should be sorted to playlists")
        if clear:
            self.clear_playlist(needs_sorting_playlist)
        offset = 0
        limit = 250
        repeat_count = 2
        previous_length = None
        my_library = set()
        total = None
        already_sorted = set()
        needs_sorting_playlist = self.get_playlist_by_name(needs_sorting_playlist)
        needs_sorting = self.get_playlist_tracks(needs_sorting_playlist)
        print(f"{len(needs_sorting)} tracks already in the sorting playlist")
        print("Now looking at user's playlists and albums")
        for plname in sort_playlists:
            print(f"   {plname}...")
            already_sorted.update(
                self.get_playlist_tracks(self.get_playlist_by_name(plname))
            )
        for album in self.get_user_albums():
            album_name = album["album"]["name"]
            print(f"   {album_name}...")
            already_sorted.update(self.get_album_tracks(album))
        print(
            f"{len(already_sorted)} tracks already sorted in user playlists and albums"
        )
        print("Loading whole library, this will take some time....")
        while repeat_count and (total is None or len(my_library) < total):
            saved_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            my_library.update(map(lambda t: t["track"]["id"], saved_tracks["items"]))
            print(f"{len(my_library)} tracks read")
            total = saved_tracks["total"]
            offset += limit
            if previous_length is not None and len(my_library) == previous_length:
                repeat_count -= 1
            previous_length = len(my_library)
        print(f"{len(my_library)} total tracks")
        to_sort = set()
        for track in my_library:
            if track not in needs_sorting and track not in already_sorted:
                to_sort.add(track)
        print(f"{len(to_sort)} tracks to sort")
        to_sort = list(to_sort)
        while len(to_sort) > 100:
            sub_tracks = to_sort[:100]
            to_sort = to_sort[100:]
            self.sp.user_playlist_add_tracks(
                self.username,
                needs_sorting_playlist["id"],
                sub_tracks,
            )
        if to_sort:
            self.sp.user_playlist_add_tracks(
                self.username,
                needs_sorting_playlist["id"],
                to_sort,
            )

    def save_discover(self):
        """
        Backup the spotify generated Discover weekly playlist.
        """
        # Find "Discover weekly" playlist
        dw = self.get_playlist_by_name("Discover Weekly")
        # Find "discover later" playlist
        dl = self.get_playlist_by_name(self.config["dl"])
        if dw is None or dl is None:
            print(f"Can't find [Discover Weekly] or [{self.config['dl']}] playlist.")
            return
        dw_tracks = self.get_playlist_tracks(dw, username="spotify")
        dl_tracks = self.get_playlist_tracks(dl)
        # Remove tracks from "discover later" if they are in library
        to_remove = []
        for track in dl_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if contained:
                to_remove.append(track)
        print(f"{len(to_remove)} tracks to remove from [{self.config['dl']}]")
        self.sp.user_playlist_remove_all_occurrences_of_tracks(
            self.username, dl["id"], to_remove
        )
        # Add tracks from "Discover weekly" to "discover later" if they are not in library
        to_add = []
        for track in dw_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if not contained and track not in dl_tracks:
                to_add.append(track)
        print(f"{len(to_add)} tracks to add to [{self.config['dl']}]")
        if to_add:
            self.sp.user_playlist_add_tracks(self.username, dl["id"], to_add)

    def shuffle(self, *plist_names):
        """
        Shuffle all the user's specified playlists.
        """
        if not plist_names:
            plist_names = self.config["rp"]
        for plist_name in plist_names:
            print(f"Shuffling playlist [{plist_name}]")
            plist = self.get_playlist_by_name(plist_name)
            if not plist:
                print("Playlist not found")
                continue
            tracks_count = plist["tracks"]["total"]
            positions = list(range(tracks_count))
            random.shuffle(positions)
            for new_pos, old_pos in enumerate(positions):
                self.sp.user_playlist_reorder_tracks(
                    self.username, plist["id"], old_pos, new_pos
                )

    def list_unhandled(self):
        """
        List all the playlist that are not in the configuration.
        """
        for plist in self.get_all_my_playlists():
            if plist["name"] not in self.config["sp"]:
                yield plist

    def find_unhandled(self):
        """
        Print all the playlist that are not in the configuration.
        """
        for plist in self.list_unhandled():
            if plist["owner"]["id"] != self.username:
                continue
            print(f"{plist['id']}: {plist['name']}")

    def find_song(self, song_url, verbose=True):
        """
        Find in which playlist this track is.
        """
        song_id = song_url.split("/")[-1]
        plists = []
        print(f"Find song [{song_id}] in playlists.")
        for plist in self.get_all_my_playlists():
            if (
                plist["name"] not in self.config["sp"]
                and plist["name"] not in self.config["rp"]
            ):
                continue
            tracks = self.get_playlist_tracks(plist)
            if song_id in tracks:
                if verbose:
                    print(plist["name"])
                plists.append(plist)
        return plists

    def get_handled_playlists(self, exclude=None):
        """
        List all the playlists that are in the configuration.
        """
        plists = []
        if exclude is None:
            exclude = []
        for plist in self.get_all_my_playlists():
            if (
                plist["name"] not in self.config["sp"]
                and plist["name"] not in self.config["rp"]
            ):
                continue
            if plist["name"] in exclude:
                continue
            plists.append(plist)
        return plists

    def find_duplicates(self, *plist_names):
        """
        Find out tracks in multiple playlists.
        """
        plists = {}
        found = []
        if plist_names:
            for plist_name in plist_names:
                plists[plist_name] = self.get_playlist_tracks(
                    self.get_playlist_by_name(plist_name), full=True
                )
        else:
            for plist in self.get_handled_playlists(exclude=self.config["nsp"]):
                plists[plist["name"]] = self.get_playlist_tracks(plist, full=True)

        for plist_name, plist_tracks in plists.items():
            other_plists = {
                pname: tracks for pname, tracks in plists.items() if pname != plist_name
            }
            if not other_plists:
                # User only gave us one playlist, compare it with all other playlists
                other_plists = {
                    plist["name"]: self.get_playlist_tracks(plist, full=True)
                    for plist in self.get_handled_playlists(exclude=self.config["nsp"])
                    if plist["name"] != plist_name
                }
            for other_name, other_tracks in other_plists.items():
                other_ids = map(lambda t: t["track"]["id"], other_tracks)
                for track in plist_tracks:
                    trackid = track["track"]["id"]
                    if trackid in found:
                        continue
                    if trackid in other_ids:
                        found.append(trackid)
                        print(
                            f"[{track['track']['name']}] is in [{plist_name}] "
                            f"and also in [{other_name}]"
                        )

    def uniq(self, *plist_names):
        """
        Remove duplicate tracks from playlists.
        """
        plists = {}
        pl_ids = {}
        if plist_names:
            for plist_name in plist_names:
                plist = self.get_playlist_by_name(plist_name)
                pl_ids[plist_name] = plist["id"]
                plists[plist_name] = self.get_playlist_tracks(plist, full=True)
        else:
            for plist in self.get_handled_playlists(exclude=self.config["nsp"]):
                pl_ids[plist["name"]] = plist["id"]
                plists[plist["name"]] = self.get_playlist_tracks(plist, full=True)

        for plist_name, plist_tracks in plists.items():
            to_remove = {}
            for idx, track in enumerate(plist_tracks):
                if track["track"]["id"] in [
                    t["track"]["id"] for t in plist_tracks[:idx]
                ]:
                    to_remove.setdefault(track["track"]["id"], []).append(idx)
            tracks = [{"uri": k, "positions": v} for k, v in to_remove.items()]
            print(f"For playlist {plist_name}, {len(tracks)} tracks to remove.")
            self.sp.user_playlist_remove_specific_occurrences_of_tracks(
                self.username,
                pl_ids[plist_name],
                tracks[:100],
            )
            if len(tracks) > 100:
                self.uniq(plist_name)

    def cache_albums(self):
        """
        Cache user's albums.
        """
        cache_filename = os.path.join(
            os.path.expanduser("~"),
            ".spotimyalbums",
        )
        cache = {}
        if os.path.exists(cache_filename):
            with open(cache_filename, "r", encoding="utf8") as fp:
                cache = json.load(fp)

        validity = cache.get("validity", 0)
        if validity > time.time():
            print("Cache is still valid, using it")
            return cache.get("albums", [])

        print("Cache is too old, refreshing it")
        cache["albums"] = self.get_user_albums()
        cache["validity"] = time.time() + 5 * 60 * 60  # 5h validity

        with open(cache_filename, "w", encoding="utf8") as fp:
            json.dump(cache, fp)
        return cache.get("albums", [])

    def albums(self):
        """
        Do stuff about user's albums.

        - cache the list
        - compute stats
        - generate a 'collection' page
        """
        albums = [Album(album) for album in self.cache_albums()]
        nb_tracks = sorted([a.track_count() for a in albums])
        # albums[0]["album"]["tracks"]["items"][0]["duration_ms"]
        durations = sorted([a.duration() for a in albums])
        randomly_chosen = [random.choice(albums) for _ in range(10)]
        print(f"Albums: {len(albums)}")
        print(
            f"Tracks: {percentile(nb_tracks, 0.05)}, "
            f"{percentile(nb_tracks, 0.5)}, "
            f"{percentile(nb_tracks, 0.95)}"
        )
        print(
            f"Duration: {ms_to_human(percentile(durations, 0.05))}, "
            f"{ms_to_human(percentile(durations, 0.5))}, "
            f"{ms_to_human(percentile(durations, 0.95))}"
        )
        print("Random selection:")
        for album in randomly_chosen:
            txt = album.txt()
            print(f" - {txt[0]}")
            for line in txt[1:]:
                print(f"   {line}")
        with open(os.path.join("html", "albums.html"), "w", encoding="utf8") as fp:
            fp.write(ALBUMS_PAGE_HEADER)
            for album in randomly_chosen:
                fp.write(f"{album.html()}\n")
            fp.write(ALBUMS_PAGE_FOOTER)
        return albums
