#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import os
import random
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
            print "Can't get token for", self.username
            sys.exit()

    def add_my_plist_tracks_to_library(self):
        save_playlists = self.config["sp"]
        print "Adding all tracks in playlists to user's library."
        for plist in self.sp.current_user_playlists()["items"]:
            if plist["name"] in save_playlists:
                self.add_playlist_tracks_to_library(plist)

    def add_playlist_tracks_to_library(self, playlist):
        print "Adding tracks from playlist '{}' to user library".format(playlist["name"])
        tracks = self.get_playlist_tracks(playlist)
        while len(tracks) > 48:
            subtracks = tracks[:48]
            self.sp.current_user_saved_tracks_add(tracks=subtracks)
            tracks = tracks[48:]
        if tracks:
            self.sp.current_user_saved_tracks_add(tracks=tracks)

    def get_playlist_by_name(self, plist_name):
        for plist in self.sp.current_user_playlists()["items"]:
            if unicode(plist["name"]) == unicode(plist_name):
                return plist

    def get_playlist_tracks(self, playlist, titles=False, username=None):
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

        field = "name" if titles else "id"
        return map(lambda t: t["track"][field], result)

    def clear_playlist(self, playlist):
        print "Clearing playlist '{}'".format(playlist)
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
        print "Loading user albums"
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
        print "Finding user tracks that should be sorted to playlists"
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
        print len(needs_sorting), "tracks already in the sorting playlist"
        for plname in sort_playlists:
            already_sorted.update(self.get_playlist_tracks(self.get_playlist_by_name(plname)))
        for album in self.get_user_albums():
            already_sorted.update(self.get_album_tracks(album))
        print len(already_sorted), "tracks already sorted in user playlists and albums"
        print "Loading whole library, this will take some time...."
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
        print len(my_library), "total tracks"
        to_sort = set()
        for track in my_library:
            if (
                track not in needs_sorting and
                track not in already_sorted
            ):
                to_sort.add(track)
        print len(to_sort), "tracks to sort"
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
            print("Can't find [Discover Weekly] or [{}] playlist.".format(self.config["dl"]))
            return
        dw_tracks = self.get_playlist_tracks(dw, username="spotify")
        dl_tracks = self.get_playlist_tracks(dl)
        # Remove tracks from "discover later" if they are in library
        to_remove = []
        for track in dl_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if contained:
                to_remove.append(track)
        print("{} tracks to remove from [{}]".format(len(to_remove), self.config["dl"]))
        self.sp.user_playlist_remove_all_occurrences_of_tracks(self.username, dl["id"], to_remove)
        # Add tracks from "Discover weekly" to "discover later" if they are not in library
        to_add = []
        for track in dw_tracks:
            contained = self.sp.current_user_saved_tracks_contains(tracks=[track])[0]
            if not contained:
                to_add.append(track)
        print("{} tracks to add to [{}]".format(len(to_add), self.config["dl"]))
        self.sp.user_playlist_add_tracks(self.username, dl["id"], to_add)

    def shuffle(self, *plist_names):
        if not plist_names:
            plist_names = self.config["rp"]
        for plist_name in plist_names:
            print("Shuffling playlist [{}]".format(plist_name))
            plist = self.get_playlist_by_name(plist_name)
            if not plist:
                continue
            tracks = self.get_playlist_tracks(plist)
            random.shuffle(tracks)
            self.sp.user_playlist_replace_tracks(self.username, plist["id"], tracks[:100])
            if len(tracks) > 100:
                while len(tracks) > 100:
                    sub_tracks = tracks[:100]
                    tracks = tracks[100:]
                    self.sp.user_playlist_add_tracks(self.username, plist["id"], sub_tracks)
            if tracks:
                self.sp.user_playlist_add_tracks(self.username, plist["id"], tracks)
