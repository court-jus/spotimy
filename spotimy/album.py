"""
Wrapper around the spotify album representation.
"""

from typing import List

from .utils import ms_to_human


class Album(dict):
    """
    An album on spotify.
    """

    def duration(self) -> int:
        """
        Get the duration (in ms) of the album.
        """
        return sum(t["duration_ms"] for t in self["album"]["tracks"]["items"])

    def track_count(self) -> int:
        """
        Get the number of tracks in the album.
        """
        return self["album"]["total_tracks"]

    def get_image(self, expected_width: int=300) -> str:
        """
        Find an image (url) in this album's images.
        """
        per_width = {abs(expected_width - i["width"]): i["url"] for i in self["album"]["images"]}
        closest = min(per_width.keys())
        return per_width[closest]

    def attributes(self) -> tuple:
        """
        Generate attributes for `txt` and `html` methods.
        """
        artists = self["album"]["artists"]
        title = self["album"]["name"]
        url = f"https://open.spotify.com/album/{self['album']['id']}"
        if len(artists) > 2:
            artists_name = f"{len(artists)} artists"
        else:
            artists_name = " & ".join(artist["name"] for artist in artists)
        return (
            artists_name,
            title,
            url,
            self.track_count(),
            ms_to_human(self.duration()),
            self["album"]["id"]
        )

    def txt(self) -> List[str]:
        """
        Text presentation of album.
        """
        artists_name, title, url, track_count, duration, album_id = self.attributes()
        return [
            f"{artists_name} - {title}",
            f" {track_count} tracks: {duration} - {url}",
        ]

    def html(self) -> str:
        """
        Generate an HTML card representation of album.
        """
        artists_name, title, url, track_count, duration, album_id = self.attributes()
        return f"""
<div class="album-card-container">
    <a href="{url}" target="_blank" rel="noopener">
        <div class="album-card" style="background-image: url('{self.get_image()}');">
            <div class="album-details">
                <h1 class="album-title">{title}</h1>
                <h2 class="album-artists">{artists_name}</h2>
                <h3 class="album-meta">{track_count}&nbsp;-&nbsp;{duration}</h3>
            </div>
        </div>
    </a>
</div>
        """
