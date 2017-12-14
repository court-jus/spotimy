#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
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


def save_config(config):
    config_filename = os.path.join(os.path.expanduser("~"), ".spotimyrc")
    with open(config_filename, "w") as fp:
        yaml.dump(config, fp, default_flow_style=False)


def create_token_file(username, client_id, client_secret, redirect_uri):
    token_params = {
        "username": username,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
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
    parser = argparse.ArgumentParser(description="Manage your spotify playlists.")
    # Edit config
    parser.add_argument(
        "--need-sorting", action="store",
        help=("Set the name of the playlist that will gather tracks that need "
              "to be sorted (must exist on Spotify)."))
    parser.add_argument(
        "--add", action="store",
        help=("Add a playlist."))
    parser.add_argument(
        "--del", dest="remove", action="store",
        help=("Remove a playlist."))
    parser.add_argument("args", nargs="*")
    # Actions
    parser.add_argument(
        "--create-token-file", action="store_true", default=False,
        help=("Create token file, args should then be "
              "USERNAME, CLIENT_ID, CLIENT_SECRET and REDIRECT_URI"))
    args = parser.parse_args()
    config = load_config()
    config.setdefault("nsp", "needs sorting")
    config.setdefault("sp", [])
    # Edit config
    new_config = {}
    if args.need_sorting:
        new_config["nsp"] = args.need_sorting
    if args.add:
        new_config["sp"] = config["sp"]
        new_config["sp"].append(args.add)
    if args.remove and args.remove in config["sp"]:
        new_config["sp"] = config["sp"]
        new_config["sp"].remove(args.remove)
    if new_config:
        config.update(new_config)
        new_config = config.copy()
        new_config.pop("token")
        save_config(new_config)
    # Actions
    if args.create_token_file:
        if len(args.args) == 4:
            create_token_file(*args.args)
        else:
            print("Wrong number of arguments for --create-token-file.")
        return
    sp = Spotimy(config)
    sp.add_my_plist_tracks_to_library()
    sp.add_library_to_sorting_plist()


if __name__ == "__main__":
    main()
