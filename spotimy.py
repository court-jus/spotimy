#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import sys


def create_token_file():
    token_params = {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uri": "YOUR_REDIRECT_URI",
    }
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "w") as fp:
        json.dump(token_params, fp)

def load_token_file():
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "r") as fp:
        token_params = json.load(fp)
    return token_params

class Spotimy(object):

    def __init__(self):
        self.get_sp_client()

    def get_sp_client(self):
        scope = 'user-library-read playlist-modify-private playlist-modify-public user-library-modify'
        token_params = load_token_file()

        if len(sys.argv) > 1:
            self.username = sys.argv[1]
        else:
            print "Usage: %s username" % (sys.argv[0],)
            sys.exit()

        token = util.prompt_for_user_token(self.username, scope, **token_params)

        if token:
            self.sp = spotipy.Spotify(auth=token)
        else:
            print "Can't get token for", self.username
            sys.exit()

    def add_my_plist_tracks_to_library(self, save_playlists):
        print "Adding all tracks in playlists to user's library."
        for plist in self.sp.current_user_playlists()["items"]:
            if plist["name"] in save_playlists:
                print plist["name"]
                self.add_playlist_tracks_to_library(plist)

    def add_playlist_tracks_to_library(self, playlist):
        tracks = self.get_playlist_tracks(playlist)
        while len(tracks) > 48:
            subtracks = tracks[:48]
            self.sp.current_user_saved_tracks_add(tracks=subtracks)
            tracks = tracks[48:]
        self.sp.current_user_saved_tracks_add(tracks=tracks)

    def get_playlist_by_name(self, plist_name):
        for plist in self.sp.current_user_playlists()["items"]:
            if unicode(plist["name"]) == unicode(plist_name):
                return plist

    def get_playlist_tracks(self, playlist, titles=False):
        if not playlist:
            return []
        tracks = self.sp.user_playlist(
            self.username, playlist["id"], fields="tracks,id")

        field = "name" if titles else "id"
        return map(lambda t: t["track"][field], tracks["tracks"]["items"])

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

    def add_library_to_sorting_plist(self, needs_sorting_playlist, sort_playlists):
        print "Search library and add un-playlisted tracks to playlist [{}]".format(
            needs_sorting_playlist,
        )
        offset = 0
        limit = 100
        biglimit = 10000
        my_library = []
        total = None
        already_sorted = []
        needs_sorting_playlist = self.get_playlist_by_name(needs_sorting_playlist)
        needs_sorting = self.get_playlist_tracks(needs_sorting_playlist)
        for plname in sort_playlists:
            already_sorted.extend(self.get_playlist_tracks(self.get_playlist_by_name(plname)))
        for album in self.get_user_albums():
            already_sorted.extend(self.get_album_tracks(album))
        print len(already_sorted), "tracks already sorted"
        print len(needs_sorting), "tracks already in need to be sorted"
        while len(my_library) < biglimit and (total is None or len(my_library) < total):
            print offset
            saved_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)

            my_library.extend(saved_tracks["items"])
            total = saved_tracks["total"]
            offset += limit
        print len(my_library), "total tracks"
        to_sort = []
        for track in my_library:
            if (
                track["track"]["id"] not in needs_sorting and
                track["track"]["id"] not in already_sorted
            ):
                to_sort.append(track["track"]["id"])
        print len(to_sort), "tracks to sort"
        self.sp.user_playlist_add_tracks(
            self.username, needs_sorting_playlist["id"],
            [track["track"]["id"], ],
        )


def main():
    sp = Spotimy()
    needs_sorting_playlist = "needs sorting"
    save_playlists = [
        "Baume au coeur", "piano", "Douceur, detente", "Swing", "OMNI",
        "Morning boost up", "Forget everything and get into a blind trance",
        "Steampunk and strange stuff", "Nostalgie", "Pump It up !!",
        "share it maybe", u"Frissons à l'unisson", "Ondulations",
        "Route 66 and other highways", "Will you dance with me ?",
        "Know me through music I love...", "Interesting covers", "MedFan", "Blues junkie",
        "Jazzy or not", "Cosy Road Trip", "Mes titres Shazam", "Rock Box",
        u"À tester, découvrir", u"Épique", "VRAC",
        "Viens danser tout contre moi", "Endless Trip on a Steel Dragonfly", "Cosy",
        "Enfants", u"Sélection", "Favoris des radios", needs_sorting_playlist,
    ]
    # sp.add_my_plist_tracks_to_library(save_playlists)
    sp.add_library_to_sorting_plist(needs_sorting_playlist, save_playlists)


if __name__ == "__main__":
    # Uncomment this after changing YOUR_CLIENT_* to
    # create the token file ~/.spotifytoken
    #
    # create_token_file()
    #
    main()
