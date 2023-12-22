"""
TheNexusAvenger

Manages tasks for the various YouTube classes.
"""

import json
import os
import Paths
from YouTube.YouTubeCacheDatabase import YouTubeCacheDatabase
from YouTube.YouTubeOAuth2Api import YouTubeOAuth2Api
from YouTube.YouTubePlaylistState import YouTubePlaylistState


class YouTubeTasks:
    def __init__(self):
        """Creates the YouTube Tasks object.
        """

        # Create the default configuration.json file.
        if not os.path.exists(Paths.configurationPath):
            with open(Paths.configurationPath, "w") as file:
                file.write(json.dumps({
                    "YouTubeApiKey": "YOUTUBE_API_KEY_HERE",
                    "Caching": {
                        "PlaylistCacheUpdateMethod": "ROLLING",
                        "PlaylistCacheTime": 720,
                        "VideoCacheTime": 720,
                        "RollingUpdateMaxLatestVideos": 10,
                        "RollingUpdateMaxOldestVideos": 50
                    },
                    "Application": {
                        "TaskLoopDelayMinutes": 30,
                    },
                    "SourcePlaylists": [
                        "SOURCE_PLAYLIST_ID_HERE"
                    ],
                    "TargetPlaylists": {
                        "#hashtag1": [
                            "TARGET_PLAYLIST_ID_HERE",
                        ],
                        "#hashtag2": [
                            "TARGET_PLAYLIST_ID_HERE",
                        ],
                    }
                }, indent=4))

        # Read the configuration.
        with open(Paths.configurationPath) as file:
            configuration = json.loads(file.read())
        if "YouTubeApiKey" not in configuration.keys():
            raise RuntimeError("YouTubeApiKey missing from configuration.")
        if configuration["YouTubeApiKey"] == "YOUTUBE_API_KEY_HERE":
            raise RuntimeError("YouTubeApiKey in configuration is the default value. See README.md for how to set it up.")
        if "SourcePlaylists" not in configuration.keys():
            raise RuntimeError("SourcePlaylists missing from configuration.")
        if "TargetPlaylists" not in configuration.keys():
            raise RuntimeError("SourcePlaylists missing from configuration.")
        if not os.path.exists(Paths.clientSecretPath):
            raise RuntimeError("client_secret.json is not found. See README.md top section for how to set it up.")
        self.configuration = configuration

        # Set up the credentials.
        apiKey = configuration["YouTubeApiKey"]
        self.cacheDatabase = YouTubeCacheDatabase(apiKey, configuration["Caching"]["VideoCacheTime"] * 60, configuration["Caching"]["PlaylistCacheTime"] * 60, configuration["Caching"]["RollingUpdateMaxLatestVideos"], configuration["Caching"]["RollingUpdateMaxOldestVideos"])
        self.oauth2Api = YouTubeOAuth2Api(apiKey, self.cacheDatabase)
        self.oauth2Api.initializeAuthorizationHeader()

    def updateCache(self) -> None:
        """Updates the playlist and video cache.
        """

        for sourcePlaylistId in self.configuration["SourcePlaylists"]:
            self.cacheDatabase.addNewPlaylistVideoIdsQuick(sourcePlaylistId)
            self.cacheDatabase.updateCachedPlaylistVideos(sourcePlaylistId, self.configuration["Caching"]["PlaylistCacheUpdateMethod"])

    def updatePlaylists(self) -> None:
        """Updates the playlists.
        """

        playlistState = YouTubePlaylistState(self.cacheDatabase, self.oauth2Api)
        for sourcePlaylistId in self.configuration["SourcePlaylists"]:
            playlistState.addSourcePlaylist(sourcePlaylistId)
        for keyword in self.configuration["TargetPlaylists"].keys():
            for playlistId in self.configuration["TargetPlaylists"][keyword]:
                playlistState.addPlaylist(playlistId, keyword)
        playlistState.updatePlaylists()

    def performActions(self) -> None:
        """Performs all actions together.
        """

        try:
            self.updateCache()
        except ConnectionError:
            print("Quota limit was reached. Cache can't be updated.")

        try:
            self.updatePlaylists()
        except ConnectionError:
            print("Quota limit was reached. Playlists can't be fetched to add videos.")
        except RuntimeError as e:
            print("Unexpected error: " + str(e))
