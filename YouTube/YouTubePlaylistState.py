"""
TheNexusAvenger

Manages the state of playlists.
"""
import os.path

import Paths
from typing import Dict, List
from YouTube.YouTubeCacheDatabase import YouTubeCacheDatabase, Video
from YouTube.YouTubeOAuth2Api import YouTubeOAuth2Api


class YouTubePlaylistStateEntry:
    def __init__(self, playlistId: str, cacheDatabase: YouTubeCacheDatabase):
        """Creates a playlist state entry.

        :param playlistId: Playlist id to manage.
        :param cacheDatabase: Cache database to get videos from.
        """

        self.playlistId = playlistId
        self.cacheDatabase = cacheDatabase
        self.keywords: List[str] = []
        self.videosToRemove: List[Video] = []
        self.videosToAdd: List[Video] = []
        self.videosToKeep: List[Video] = []

    def addKeyword(self, keyword: str) -> None:
        """Adds a keyword for the videos to be part of the playlist.

        :param keyword: Keyword to match for (case-insensitive).
        """

        keyword = keyword.lower()
        if keyword not in self.keywords:
            self.keywords.append(keyword)

    def readVideos(self, videoIds: List[str]) -> None:
        """Populates the video lists with the video ids.

        :param videoIds: Video ids to check.
        """

        # Get the current playlist ids.
        playlistVideoIds = self.cacheDatabase.listPlaylistVideoIds(self.playlistId)

        # Iterate over the video ids.
        for videoId in videoIds:
            # Check if the video contains the keyword.
            videoData = self.cacheDatabase.getCachedVideo(videoId)
            containsKeyword = False
            for keyword in self.keywords:
                if keyword in videoData.title.lower() or keyword in videoData.description.lower():
                    containsKeyword = True
                    break

            # Add the video.
            if containsKeyword:
                if videoId in playlistVideoIds:
                    self.videosToKeep.append(videoData)
                else:
                    self.videosToAdd.append(videoData)
            elif videoId in playlistVideoIds:
                self.videosToRemove.append(videoData)

    def writeReport(self) -> None:
        """Writes a report with the video lists.
        """

        # Create the reports directory.
        if not os.path.exists(Paths.reportsPath):
            os.mkdir(Paths.reportsPath)

        # Write the report.
        with open(os.path.join(Paths.reportsPath, self.playlistId + ".txt"), "w", encoding="utf8") as file:
            # Write the videos to remove.
            file.write("Videos to remove (manual action required):")
            for video in self.videosToRemove:
                file.write("\n- https://www.youtube.com/watch?v=" + video.id + " (" + video.title + ")")

            # Write the videos to add.
            file.write("\n\nVideos to add (not added yet due to quota limits):")
            for video in self.videosToAdd:
                file.write("\n- https://www.youtube.com/watch?v=" + video.id + " (" + video.title + ")")

            # Write the videos to add.
            file.write("\n\nVideos to keep:")
            for video in self.videosToKeep:
                file.write("\n- https://www.youtube.com/watch?v=" + video.id + " (" + video.title + ")")

    def reset(self) -> None:
        """Resets the video lists.
        """

        self.videosToRemove = []
        self.videosToAdd = []
        self.videosToKeep = []


class YouTubePlaylistState:
    def __init__(self, cacheDatabase: YouTubeCacheDatabase, oauth2Api: YouTubeOAuth2Api):
        """Creates a playlist state.

        :param cacheDatabase: YouTube cache database for videos and playlists.
        :param oauth2Api: YouTube OAuth2 API helper.
        """

        self.cacheDatabase = cacheDatabase
        self.oauth2Api = oauth2Api
        self.playlistEntries: Dict[str, YouTubePlaylistStateEntry] = {}
        self.videoIds = []

    def addSourcePlaylist(self, playlistId: str) -> None:
        """Adds a source playlist to pull from.

        :param playlistId: Playlist id to add.
        """

        for videoId in self.cacheDatabase.listPlaylistVideoIds(playlistId):
            if videoId not in self.videoIds:
                self.videoIds.append(videoId)

    def addPlaylist(self, playlistId: str, keyword: str) -> None:
        """Adds a target playlist and keyword.

        :param playlistId: Playlist id to manage.
        :param keyword: Keyword for the playlist to use.
        """

        if playlistId not in self.playlistEntries.keys():
            self.playlistEntries[playlistId] = YouTubePlaylistStateEntry(playlistId, self.cacheDatabase)
        self.playlistEntries[playlistId].addKeyword(keyword)

    def buildVideoLists(self) -> None:
        """Builds the lists in all the playlist entries.
        """

        for playlistEntry in self.playlistEntries.values():
            playlistEntry.reset()
            playlistEntry.readVideos(self.videoIds)

    def updatePlaylists(self) -> None:
        """Builds the playlist entries, adds the playlist videos, and write the reports.
        """

        # Build the video lists.
        print("Building playlists.")
        self.buildVideoLists()

        # Add the videos to the playlist.
        quotaExceeded = False
        completedAdditions = 0
        pendingOperations = 0
        for playlistEntry in self.playlistEntries.values():
            for video in playlistEntry.videosToAdd:
                if quotaExceeded:
                    pendingOperations += 1
                else:
                    try:
                        # Add the video.
                        self.oauth2Api.addToPlaylist(playlistEntry.playlistId, video.id)
                        completedAdditions += 1
                    except ConnectionError:
                        # Print that the quota was exceeded.
                        print("API quota was exceeded. Unable to perform any more operations for the rest of the day.")
                        quotaExceeded = True
                        pendingOperations += 1

        # Output the reports.
        print("Added " + str(completedAdditions) + " video(s) with " + str(pendingOperations) + " video(s) pending due to the resource quota. See the reports for manual actions.")
        self.buildVideoLists()
        for playlistEntry in self.playlistEntries.values():
            playlistEntry.writeReport()
