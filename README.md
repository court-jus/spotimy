# spotimy
Script to help with spotify library management

## Description

I wrote this script because I almost only listen to playlist on spotify
but I add tracks to my library on a regular basis and never listen to
them if they are not in playlists.

So, the first goal was to create a playlist to gather all the tracks in
my library that were not already in an existing playlist.

As a bonus, I want to be sure that all the tracks in my playlists are
also added to my library so if I edit or remove tracks from playlists
they are not "lost".

Disclaimer: The script was written for my own personnal use and is
probably full of bugs and missing features. I am working on it but may
abandon it anytime if I lose interest. I am open to contributions and
issues from users. There is no GUI and probably will never be, it is
only tested on linux (Ubuntu and Debian).

## Installation

I suggest you create a dedicated virtualenv and install dependencies with
pip:

    git clone https://github.com/court-jus/spotimy.git
    cd spotimy
    virtualenv .venv
    . ./.venv/bin/activate
    pip install -Ur requirements.txt

## Usage

The script uses a config file, stored in ~/.spotimyrc in yaml format, there
is an example in the examples folder that you can copy and edit to fit your
own needs.

The "nsp" is the name of the playlist that will be filled with tracks that
need to be sorted (this playlist should exist on Spotify).

"sp" is a list of playlists that already contain tracks and should be used
to check if tracks are already sorted or not.

There is also a tokefile, stored in ~/.spotifytoken, in yaml format too.
There is also an example. You can get your token informations on the spotify
developer page: https://developer.spotify.com/my-applications/

When everything is setup, launch the script with

    python main.py --help

## Actions

### Add to library

It will gather tracks from all your "sp" playlists and add them to
your library.

### Sort library

Each track that is in your library but not in any of
your "sp" playlist nor in any of your "saved albums" on Spotify will be
added to your "nsp" playlist.
