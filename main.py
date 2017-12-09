#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spotimy.client import Spotimy


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
        u"À tester, découvrir", u"Épique", "VRAC", "Hard as metal",
        "Viens danser tout contre moi", "Endless Trip on a Steel Dragonfly", "Cosy",
        "Enfants", u"Sélection", "Favoris des radios", needs_sorting_playlist,
    ]
    # sp.add_my_plist_tracks_to_library(save_playlists)
    # sp.add_library_to_sorting_plist(needs_sorting_playlist, save_playlists)


if __name__ == "__main__":
    # Uncomment this after changing YOUR_CLIENT_* to
    # create the token file ~/.spotifytoken
    #
    # create_token_file()
    #
    main()
