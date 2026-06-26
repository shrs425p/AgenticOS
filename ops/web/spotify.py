"""Module for spotify.py"""
from __future__ import annotations

import re


from kernel.base import tool
class SpotifyMixin:
    @tool(name="findspotifytrack", desc="Find Spotify track link. Args: title, artist (optional)", category="Web")
    def findspotifytrack(self, title: str, artist: str = "") -> str:
        """Find an open.spotify.com/track URL for a given song using the search engine."""
        q = (title or "").strip()
        a = (artist or "").strip()
        if not q:
            return "Error: title required."

        query = f'"{q}" {a} site:open.spotify.com track'.strip()
        try:
            # Use the robust search mixin instead of the limited DDG API
            search_results = self.search(query, num_results="5")

            # Extract Spotify track URLs using regex
            track_urls = re.findall(
                r"https?://open\.spotify\.com/track/[A-Za-z0-9?=&]+", search_results
            )

            if not track_urls:
                # Try a broader search if the specific one fails
                query_broad = f"{q} {a} spotify track".strip()
                search_results = self.search(query_broad, num_results="5")
                track_urls = re.findall(
                    r"https?://open\.spotify\.com/track/[A-Za-z0-9?=&]+", search_results
                )

            if track_urls:
                # Return the first clean track URL
                return track_urls[0].split("?")[0]

            return "Error: Could not find a Spotify track link in search results."
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    @tool(name="playspotifytrack", desc="Find and immediately play a song on Spotify. Args: title, artist (optional)", category="Web")
    def playspotifytrack(self, title: str, artist: str = "") -> str:
        """Find and immediately play a song on Spotify.

        Args:
            title:  Song title
            artist: Artist name (optional)
        """
        url = self.findspotifytrack(title, artist)
        if url.startswith("Error:"):
            return url

        # Use openurl (inherited via OpenersMixin/WebTools) to launch the track
        # On Windows/Mac, this opens the Spotify app and starts playback.
        try:
            # We assume openurl is available on the instance
            if hasattr(self, "openurl"):
                self.openurl(url)
                return f"Playing: {title} by {artist} ({url})"
            return f"Found track but openurl not available: {url}"
        except Exception as e:
            return f"Error launching playback: {e}"
