"""
A CLI to manage user's library.
"""

import argparse
import os

import yaml  # type: ignore
from yaml.loader import BaseLoader  # type: ignore

from spotimy.client import Spotimy


def load_config():
    """
    Load configuration from file.
    """
    config_filename = os.path.join(os.path.expanduser("~"), ".spotimyrc")
    config = {}
    if os.path.exists(config_filename):
        with open(config_filename, "r", encoding="utf8") as fp:
            config = yaml.load(fp, BaseLoader)
    if os.path.exists(os.path.join(os.path.expanduser("~"), ".spotifytoken")):
        config["token"] = load_token_file()
    return config


def save_config(config):
    """
    Save configuration file.
    """
    config_filename = os.path.join(os.path.expanduser("~"), ".spotimyrc")
    with open(config_filename, "w", encoding="utf8") as fp:
        yaml.dump(config, fp, default_flow_style=False)


def create_token_file(username, client_id, client_secret, redirect_uri):
    """
    Create token file from arguments.
    """
    token_params = {
        "username": username,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "w", encoding="utf8") as fp:
        yaml.dump(token_params, fp, default_flow_style=False)


def load_token_file():
    """
    Load authentication token from file.
    """
    token_filename = os.path.join(os.path.expanduser("~"), ".spotifytoken")
    with open(token_filename, "r", encoding="utf8") as fp:
        token_params = yaml.load(fp, BaseLoader)
    return token_params


def main() -> None:
    """
    Entrypoint for the CLI.
    """
    parser = argparse.ArgumentParser(description="Manage your spotify playlists.")
    # Edit config
    parser.add_argument(
        "--need-sorting", action="store",
        help=("Set the name of the playlist that will gather tracks that need "
              "to be sorted (must exist on Spotify)."))
    parser.add_argument(
        "--discover", action="store",
        help=("Set the name of the playlist that will gather tracks from "
              "discover weekly (must exist on Spotify)."))
    parser.add_argument(
        "--add", action="store",
        help="Add a playlist.")
    parser.add_argument(
        "--del", dest="remove", action="store",
        help="Remove a playlist.")
    parser.add_argument(
        "--add-rp", action="store",
        help="Add a playlist to be randomized.")
    parser.add_argument(
        "--del-rp", dest="remove_rp", action="store",
        help="Remove a playlist from randomized ones.")
    parser.add_argument("args", nargs="*")
    # Actions
    parser.add_argument(
        "--create-token-file", action="store_true", default=False,
        help=("Create token file, args should then be "
              "USERNAME, CLIENT_ID, CLIENT_SECRET and REDIRECT_URI"))
    parser.add_argument(
        "--add-to-library", action="store_true", default=False,
        help="Add tracks from playlist to user library.")
    parser.add_argument(
        "--sort-library", action="store_true", default=False,
        help=("Add tracks from library but not in any playlist to "
              "the dedicated 'need sorting' playlist."))
    parser.add_argument(
        "--save-discover", action="store_true", default=False,
        help=("Add tracks from discover weekly that are not in library "
              "to 'discover later' playlist, also remove from that "
              "playlist tracks that are in library."))
    parser.add_argument(
        "--shuffle", action="store_true", default=False,
        help="Shuffle the playlists listed in the 'rp' config section.")
    parser.add_argument(
        "--find-unhandled", action="store_true", default=False,
        help="Find playlists that are not in the config file.")
    parser.add_argument(
        "--find-song", action="store",
        help="Find playlists that contain that song.")
    parser.add_argument(
        "--find-duplicates", action="store_true", default=False,
        help="Find duplicates (song in multiple playlists.")
    parser.add_argument(
        "--cron", action="store_true", default=False,
        help="Run cron job")
    parser.add_argument(
        "--uniq", action="store_true", default=False,
        help="Remove duplicated songs in playlists")
    parser.add_argument(
        "--albums", action="store_true", default=False,
        help="Show stats about albums and generate albums page")
    args = parser.parse_args()
    config = load_config()
    config.setdefault("nsp", "needs sorting")
    config.setdefault("dl", "discover later")
    config.setdefault("sp", [])
    config.setdefault("rp", [])
    # Edit config
    new_config = {}
    if args.need_sorting:
        new_config["nsp"] = args.need_sorting
    if args.discover:
        new_config["dl"] = args.discover
    if args.add:
        add = args.add
        if add not in config["sp"]:
            new_config["sp"] = config["sp"]
            new_config["sp"].append(add)
    if args.remove:
        remove = args.remove
        if remove in config["sp"]:
            new_config["sp"] = config["sp"]
            new_config["sp"].remove(remove)
    if args.add_rp:
        add_rp = args.add_rp
        if add_rp not in config["rp"]:
            new_config["rp"] = config["rp"]
            new_config["rp"].append(add_rp)
    if args.remove_rp:
        remove_rp = args.remove_rp
        if remove_rp in config["rp"]:
            new_config["rp"] = config["rp"]
            new_config["rp"].remove(remove_rp)
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
    if args.save_discover:
        sp.save_discover()
    if args.add_to_library:
        sp.add_my_plist_tracks_to_library()
    if args.sort_library:
        sp.add_library_to_sorting_plist()
    if args.shuffle:
        plist_names = args.args
        sp.shuffle(*plist_names)
    if args.find_unhandled:
        sp.find_unhandled()
    if args.find_song:
        sp.find_song(args.find_song)
    if args.find_duplicates:
        sp.find_duplicates(*args.args)
    if args.uniq:
        sp.uniq(*args.args)
    if args.cron:
        sp.add_my_plist_tracks_to_library()
        sp.add_library_to_sorting_plist()
        sp.shuffle()
    if args.albums:
        sp.albums()


if __name__ == "__main__":
    main()
