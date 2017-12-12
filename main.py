#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import os
from spotimy.client import Spotimy


def load_config():
    config_filename = os.path.join(os.path.expanduser("~"), ".spotimyrc")
    config = {}
    if os.path.exists(config_filename):
        with open(config_filename, "r") as fp:
            config = yaml.load(fp)
    config["token"] = load_token_file()
    return config


def create_token_file():
    token_params = {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uri": "YOUR_REDIRECT_URI",
    }
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "w") as fp:
        yaml.dump(token_params, fp, default_flow_style=False)


def load_token_file():
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "r") as fp:
        token_params = yaml.load(fp)
    return token_params


def main():
    config = load_config()
    config.setdefault("needs_sorting_playlist", "needs sorting")
    config.setdefault("save_playlists", [])
    sp = Spotimy(config)
    sp.add_my_plist_tracks_to_library()
    sp.add_library_to_sorting_plist()


if __name__ == "__main__":
    # Uncomment this after changing YOUR_CLIENT_* to
    # create the token file ~/.spotifytoken
    #
    # create_token_file()
    #
    main()
