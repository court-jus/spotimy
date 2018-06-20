#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import os
import pdb  # noqa
import random
from spotimy.tools import uprint
import spotimy.concurrency
import spotipy
from spotipy.client import SpotifyException
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import sys
import time


class Spotimy(object):

    def __init__(self, config):
        self.config = config
        self.get_sp_client()

    def get_sp_client(self):
        scope = ('user-library-read playlist-modify-private '
                 'playlist-modify-public user-library-modify '
                 'playlist-read-private '
                 )
        token_params = self.config["token"]

        self.username = token_params.pop("username")
        token = util.prompt_for_user_token(self.username, scope, **token_params)

        if token:
            self.sp = spotipy.Spotify(auth=token)
        else:
            uprint("Can't get token for {}".format(self.username))
            sys.exit()

    def get_all_my_playlists(self):
        result = []
        playlists = self.sp.current_user_playlists()
        while playlists:
            result.extend(playlists["items"])
            if not playlists["next"]:
                break
            playlists = self.sp.next(playlists)
        return result

    def add_my_plist_tracks_to_library(self):
        save_playlists = self.config["sp"]
        uprint("Adding all tracks in playlists to user's library.")
        for plist in self.get_all_my_playlists():
            if plist["name"] in save_playlists:
                self.add_playlist_tracks_to_library(plist)

    def add_playlist_tracks_to_library(self, playlist):
        uprint("Adding tracks from playlist '{}' to user library".format(playlist["name"]))
        tracks = self.get_playlist_tracks(playlist)
        contained = spotimy.concurrency.do_bunch(
            self.sp.current_user_saved_tracks_contains,
            kwargs={"tracks": tracks},
            items_kwarg="tracks",
            limit=50,
        )
        contained = zip(tracks, contained)
        tracks = [trackid for trackid, already in contained if not already]
        if tracks:
            spotimy.concurrency.do_bunch(
                self.sp.current_user_saved_tracks_add,
                kwargs={"tracks": tracks},
                items_kwarg="tracks",
                limit=50,
            )

    def get_playlist_by_name(self, plist_name):
        for plist in self.get_all_my_playlists():
            if unicode(plist["name"]) == unicode(plist_name):
                return plist

    def get_playlist_tracks(self, playlist, titles=False, username=None, full=False):
        if not playlist:
            return []
        if username is None:
            username = self.username
        result = spotimy.concurrency.get_whole(
            self.sp.user_playlist_tracks,
            username, playlist["id"],
        )

        if full:
            return result
        field = "name" if titles else "id"
        return map(lambda t: t["track"][field], result)

    def clear_playlist(self, playlist):
        uprint("Clearing playlist '{}'".format(playlist))
        playlist = self.get_playlist_by_name(playlist)
        tracks = self.get_playlist_tracks(playlist)
        spotimy.concurrency.do_bunch(
            self.sp.user_playlist_remove_all_occurrences_of_tracks,
            items_arg=2,
            args=[self.username, playlist["id"], tracks],
        )

    def get_album_tracks(self, album, titles=False):
        if not album:
            return []
        result = spotimy.concurrency.get_album_tracks(self.sp, album)
        field = "name" if titles else "id"
        return map(lambda t: t[field], result)

    def get_user_albums(self):
        uprint("Loading user albums")
        return spotimy.concurrency.get_user_albums(self.sp)

    def add_library_to_sorting_plist(self, clear=True):
        needs_sorting_playlist = self.config["nsp"]
        sort_playlists = self.config["sp"]
        uprint("Finding user tracks that should be sorted to playlists")
        if clear:
            self.clear_playlist(needs_sorting_playlist)
        already_sorted = set()
        needs_sorting_playlist = self.get_playlist_by_name(needs_sorting_playlist)
        needs_sorting = self.get_playlist_tracks(needs_sorting_playlist)
        uprint("{} tracks already in the sorting playlist".format(len(needs_sorting)))
        for plname in sort_playlists:
            already_sorted.update(self.get_playlist_tracks(self.get_playlist_by_name(plname)))
        for album in self.get_user_albums():
            already_sorted.update(self.get_album_tracks(album))
        uprint("tracks already sorted in user playlists and albums".format(len(already_sorted)))
        uprint("Loading whole library, this will take some time....")
        my_library = map(
            lambda t: t["track"]["id"],
            spotimy.concurrency.get_whole(self.sp.current_user_saved_tracks)
        )
        uprint("{} total tracks".format(len(my_library)))
        to_sort = set()
        for track in my_library:
            if (
                track not in needs_sorting and
                track not in already_sorted
            ):
                to_sort.add(track)
        uprint("{} tracks to sort".format(len(to_sort)))
        to_sort = list(to_sort)
        spotimy.concurrency.do_bunch(
            self.sp.user_playlist_add_tracks,
            args=[self.username, needs_sorting_playlist["id"], to_sort],
            items_arg=2,
        )

    def save_discover(self):
        # Find "Discover weekly" playlist
        dw = self.get_playlist_by_name("Discover Weekly")
        # Find "discover later" playlist
        dl = self.get_playlist_by_name(self.config["dl"])
        if dw is None or dl is None:
            uprint("Can't find [Discover Weekly] or [{}] playlist.".format(self.config["dl"]))
            return
        dw_tracks = self.get_playlist_tracks(dw, username="spotify")
        dl_tracks = self.get_playlist_tracks(dl)
        # Remove tracks from "discover later" if they are in library
        to_remove = []
        for track in dl_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if contained:
                to_remove.append(track)
        uprint("{} tracks to remove from [{}]".format(len(to_remove), self.config["dl"]))
        spotimy.concurrency.do_bunch(
            self.sp.user_playlist_remove_all_occurrences_of_tracks,
            args=[self.username, dl["id"], to_remove],
            items_arg=2,
        )
        # Add tracks from "Discover weekly" to "discover later" if they are not in library
        to_add = []
        for track in dw_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if not contained and track not in dl_tracks:
                to_add.append(track)
        uprint("{} tracks to add to [{}]".format(len(to_add), self.config["dl"]))
        if to_add:
            spotimy.concurrency.do_bunch(
                self.sp.user_playlist_add_tracks,
                args=[self.username, dl["id"], to_add],
                items_arg=2,
            )

    def shuffle(self, *plist_names):
        if not plist_names:
            plist_names = self.config["rp"]
        for plist_name in plist_names:
            uprint("Shuffling playlist [{}]".format(plist_name))
            plist = self.get_playlist_by_name(plist_name)
            if not plist:
                continue
            tracks_count = plist["tracks"]["total"]
            positions = list(range(tracks_count))
            random.shuffle(positions)
            for new_pos, old_pos in enumerate(positions):
                done = False
                while not done:
                    try:
                        self.sp.user_playlist_reorder_tracks(
                            self.username, plist["id"], old_pos, new_pos)
                    except SpotifyException as e:
                        if e.http_status == 429:
                            # API rate limit exceeded
                            # Retry later
                            print("API rate limit exceeded, sleep 1")
                            time.sleep(1)
                    else:
                        done = True

    def list_unhandled(self):
        for plist in self.get_all_my_playlists():
            if unicode(plist["name"]) not in self.config["sp"]:
                yield plist

    def find_unhandled(self):
        for plist in self.list_unhandled():
            if plist["owner"]["id"] != self.username:
                continue
            uprint("{id}: {name}".format(**plist))

    def find_song(self, song_url, verbose=True):
        song_id = song_url.split("/")[-1]
        plists = []
        uprint("Find song [{}] in playlists.".format(song_id))
        for plist in self.get_all_my_playlists():
            if plist["name"] not in self.config["sp"] and plist["name"] not in self.config["rp"]:
                continue
            tracks = self.get_playlist_tracks(plist)
            if song_id in tracks:
                if verbose:
                    uprint(plist["name"])
                plists.append(plist)
        return plists

    def get_handled_playlists(self, exclude=None):
        plists = []
        if exclude is None:
            exclude = []
        for plist in self.get_all_my_playlists():
            if plist["name"] not in self.config["sp"] and plist["name"] not in self.config["rp"]:
                continue
            if plist["name"] in exclude:
                continue
            plists.append(plist)
        return plists

    def find_duplicates(self, *plist_names):
        plists = {}
        found = []
        if plist_names:
            for plist_name in plist_names:
                plists[plist_name] = self.get_playlist_tracks(
                    self.get_playlist_by_name(plist_name), full=True)
        else:
            for plist in self.get_handled_playlists(exclude=self.config["nsp"]):
                plists[plist["name"]] = self.get_playlist_tracks(plist, full=True)

        for plist_name, plist_tracks in plists.items():
            other_plists = {
                pname: tracks
                for pname, tracks in plists.items()
                if pname != plist_name
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
                        uprint("[{}] is in [{}] ans also in [{}]".format(
                            track["track"]["name"], plist_name, other_name))

    def uniq(self, *plist_names):
        plists = {}
        found = []
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
                if track["track"]["id"] in [t["track"]["id"] for t in plist_tracks[:idx]]:
                    to_remove.setdefault(track["track"]["id"], []).append(idx)
            tracks = [{"uri": k, "positions": v} for k, v in to_remove.items()]
            uprint("For playlist {}, {} tracks to remove.".format(plist_name, len(tracks)))
            spotimy.concurrency.do_bunch(
                self.sp.user_playlist_remove_specific_occurrences_of_tracks,
                args=[self.username, pl_ids[plist_name], tracks],
                items_arg=2,
            )
