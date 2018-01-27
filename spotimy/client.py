#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import os
import pdb  # noqa
import random
from spotimy.tools import uprint
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import sys


class Spotimy(object):

    def __init__(self, config):
        self.config = config
        self.get_sp_client()

    def get_sp_client(self):
        scope = 'user-library-read playlist-modify-private playlist-modify-public user-library-modify'
        token_params = self.config["token"]

        self.username = token_params.pop("username")
        token = util.prompt_for_user_token(self.username, scope, **token_params)

        if token:
            self.sp = spotipy.Spotify(auth=token)
        else:
            uprint("Can't get token for {}".format(self.username))
            sys.exit()

    def add_my_plist_tracks_to_library(self):
        save_playlists = self.config["sp"]
        uprint("Adding all tracks in playlists to user's library.")
        for plist in self.sp.current_user_playlists()["items"]:
            if plist["name"] in save_playlists:
                self.add_playlist_tracks_to_library(plist)

    def add_playlist_tracks_to_library(self, playlist):
        uprint("Adding tracks from playlist '{}' to user library".format(playlist["name"]))
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
        for plist in self.sp.current_user_playlists()["items"]:
            if unicode(plist["name"]) == unicode(plist_name):
                return plist

    def get_playlist_tracks(self, playlist, titles=False, username=None, full=False):
        if not playlist:
            return []
        if username is None:
            username = self.username
        result = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        while (len(result) < biglimit and (total is None or len(result) < total)):
            sub = self.sp.user_playlist_tracks(
                username, playlist["id"], limit=limit, offset=offset)
            result.extend(sub["items"])
            total = sub["total"]
            offset += limit

        if full:
            return result
        field = "name" if titles else "id"
        return map(lambda t: t["track"][field], result)

    def clear_playlist(self, playlist):
        uprint("Clearing playlist '{}'".format(playlist))
        playlist = self.get_playlist_by_name(playlist)
        tracks = self.get_playlist_tracks(playlist)
        if len(tracks) < 100:
            self.sp.user_playlist_remove_all_occurrences_of_tracks(
                self.username, playlist["id"], tracks)
        else:
            while len(tracks):
                sub_tracks = tracks[:100]
                tracks = tracks[100:]
                self.sp.user_playlist_remove_all_occurrences_of_tracks(
                    self.username, playlist["id"], sub_tracks)

    def get_album_tracks(self, album, titles=False):
        if not album:
            return []
        result = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        album_id = album["album"]["id"]
        while (len(result) < biglimit and (total is None or len(result) < total)):
            sub= self.sp.album_tracks(album_id, limit=limit, offset=offset)
            result.extend(sub["items"])
            total = sub["total"]
            offset += limit
        field = "name" if titles else "id"
        return map(lambda t: t[field], result)

    def get_user_albums(self):
        uprint("Loading user albums")
        albums = []
        limit = 50
        biglimit = 1000
        offset = 0
        total = None
        while (len(albums) < biglimit and (total is None or len(albums) < total)):
            subalbums = self.sp.current_user_saved_albums(limit=limit, offset=offset)
            albums.extend(subalbums["items"])
            total = subalbums["total"]
            offset += limit
        return albums

    def add_library_to_sorting_plist(self, clear=True):
        needs_sorting_playlist = self.config["nsp"]
        sort_playlists = self.config["sp"]
        uprint("Finding user tracks that should be sorted to playlists")
        if clear:
            self.clear_playlist(needs_sorting_playlist)
        offset = 0
        limit = 50
        repeat_count = 2
        previous_length = None
        my_library = set()
        total = None
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
        while repeat_count and (total is None or len(my_library) < total):
            saved_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            my_library.update(
                map(lambda t: t["track"]["id"], saved_tracks["items"])
            )
            total = saved_tracks["total"]
            offset += limit
            if previous_length is not None and len(my_library) == previous_length:
                repeat_count -= 1
            previous_length = len(my_library)
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
        while len(to_sort) > 100:
            sub_tracks = to_sort[:100]
            to_sort = to_sort[100:]
            self.sp.user_playlist_add_tracks(
                self.username, needs_sorting_playlist["id"], sub_tracks,
            )
        if to_sort:
            self.sp.user_playlist_add_tracks(
                self.username, needs_sorting_playlist["id"], to_sort,
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
        self.sp.user_playlist_remove_all_occurrences_of_tracks(self.username, dl["id"], to_remove)
        # Add tracks from "Discover weekly" to "discover later" if they are not in library
        to_add = []
        for track in dw_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if not contained and track not in dl_tracks:
                to_add.append(track)
        uprint("{} tracks to add to [{}]".format(len(to_add), self.config["dl"]))
        if to_add:
            self.sp.user_playlist_add_tracks(self.username, dl["id"], to_add)

    def shuffle(self, *plist_names):
        if not plist_names:
            plist_names = self.config["rp"]
        for plist_name in plist_names:
            uprint("Shuffling playlist [{}]".format(plist_name))
            plist = self.get_playlist_by_name(plist_name)
            if not plist:
                continue
            tracks = self.get_playlist_tracks(plist)
            random.shuffle(tracks)
            self.sp.user_playlist_replace_tracks(self.username, plist["id"], tracks[:100])
            tracks = tracks[100:]
            while len(tracks) > 100:
                sub_tracks = tracks[:100]
                tracks = tracks[100:]
                self.sp.user_playlist_add_tracks(self.username, plist["id"], sub_tracks)
            if tracks:
                self.sp.user_playlist_add_tracks(self.username, plist["id"], tracks)

    def list_unhandled(self):
        for plist in self.sp.current_user_playlists()["items"]:
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
        for plist in self.sp.current_user_playlists()["items"]:
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
        for plist in self.sp.current_user_playlists()["items"]:
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
