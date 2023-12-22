"""
TheNexusAvenger

Fetches data from YouTube with caching.
"""

import json
import requests
import sqlite3
import Paths
from datetime import datetime
from typing import List
from multiprocessing.pool import ThreadPool


class Video:
    id: str
    title: str
    description: str


class YouTubeCacheDatabase:
    def __init__(self, youTubeApiKey: str, videoCacheTimeSeconds: int, playlistCacheTimeSeconds: int, rollingUpdateMaxLatestVideos: int, rollingUpdateMaxOldestVideos: int):
        """Creates the cache database.

        :param youTubeApiKey: API key for calling YouTube.
        :param videoCacheTimeSeconds: Time to cache video data.
        :param playlistCacheTimeSeconds: Time to cache playlist data.
        :param rollingUpdateMaxLatestVideos: Max latest videos to update with the rolling method.
        :param rollingUpdateMaxOldestVideos: Max oldest videos to update with the rolling method.
        """

        self.youTubeApiKey = youTubeApiKey
        self.videoCacheTimeSeconds = videoCacheTimeSeconds
        self.playlistCacheTimeSeconds = playlistCacheTimeSeconds
        self.rollingUpdateMaxLatestVideos = rollingUpdateMaxLatestVideos
        self.rollingUpdateMaxOldestVideos = rollingUpdateMaxOldestVideos

        # Prepare the database.
        database = self.openConnection()
        database.execute("CREATE TABLE IF NOT EXISTS YouTubeVideos (VideoId TEXT PRIMARY KEY, FetchTime TEXT NOT NULL, Title TEXT NOT NULL, Description TEXT NOT NULL);")
        database.execute("CREATE TABLE IF NOT EXISTS PlaylistIds (PlaylistId TEXT PRIMARY KEY, FetchTime TEXT NOT NULL, VideoIds TEXT NOT NULL);")
        database.close()

    def openConnection(self) -> sqlite3.Connection:
        """Opens a SQLite connection.

        :return: SQLite connection to use.
        """

        return sqlite3.connect(Paths.cacheDatabasePath)

    def getVideoCacheTime(self, videoId) -> datetime:
        """Returns the last time the video was fetched.

        :param videoId: Video id to check.
        :return: Last fetch time of the video.
        """

        # Insert the video id record if it does not exist.
        database = self.openConnection()
        if database.execute("SELECT VideoId FROM YouTubeVideos WHERE VideoId = ? LIMIT 1;", [videoId]).fetchone() is None:
            database.execute("INSERT INTO YouTubeVideos VALUES (?,?,'','');", [videoId, datetime.fromisocalendar(1970, 1, 1).isoformat()])
            database.commit()

        # Get the last fetch time.
        lastFetchTime = datetime.fromisoformat(database.execute("SELECT FetchTime FROM YouTubeVideos WHERE VideoId = ? LIMIT 1;", [videoId]).fetchone()[0])
        database.close()
        return lastFetchTime

    def getCachedVideo(self, videoId: str) -> Video:
        """Returns the data of a video that is cached.
        A call to update the cache *must* be used before using thsi.

        :param videoId: Video id to fetch.
        :return: Data for the video.
        """

        database = self.openConnection()
        videoData = database.execute("SELECT Title, Description FROM YouTubeVideos WHERE VideoId = ? LIMIT 1;", [videoId]).fetchone()
        video = Video()
        video.id = videoId
        video.title = videoData[0]
        video.description = videoData[1]
        database.close()
        return video

    def getVideo(self, videoId: str, cacheTime: int = None) -> Video:
        """Returns the data of a video.
        The results are cached.

        :param videoId: Video id to fetch.
        :param cacheTime: Optional time (in seconds) to cache video results.
        :return: Data for the video.
        """

        # Set the cache time if it isn't defined.
        if cacheTime is None:
            cacheTime = self.videoCacheTimeSeconds

        # Update the record if the cached value is too old.
        currentTime = datetime.now()
        lastFetchTime = self.getVideoCacheTime(videoId)
        if (currentTime - lastFetchTime).total_seconds() > cacheTime:
            print("Fetching updated title and description for " + videoId)
            database = self.openConnection()
            youTubeVideoDataResponse = requests.get("https://www.googleapis.com/youtube/v3/videos?part=snippet&id=" + videoId + "&key=" + self.youTubeApiKey)
            youTubeVideoData = youTubeVideoDataResponse.json()
            if youTubeVideoDataResponse.status_code == 403 and "quotaExceeded" in youTubeVideoDataResponse.text:
                raise ConnectionError("YouTube API quota exceeded.")
            if "items" not in youTubeVideoData.keys():
                raise RuntimeError("Error while getting YouTube video (HTTP " + str(youTubeVideoDataResponse.status_code) + "): " + str(youTubeVideoData))
            title = youTubeVideoData["items"][0]["snippet"]["title"]
            description = youTubeVideoData["items"][0]["snippet"]["description"]
            database.execute("UPDATE YouTubeVideos SET FetchTime = ?, Title = ?, Description = ? WHERE VideoId = ?;", [currentTime.isoformat(), title, description, videoId])
            database.commit()
            database.close()

        # Return the video.
        return self.getCachedVideo(videoId)

    def updateCachedVideo(self, videoId: str) -> None:
        """Updates a cached video entry.

        :param videoId: Video id to update.
        """

        self.getVideo(videoId, 0)

    def listPlaylistVideoIds(self, playlistId: str) -> List[str]:
        """Lists the video ids in a playlist.
        The results are cached.

        :param playlistId: Id of the playlist to fetch.
        :return: Data for the video.
        """

        # Insert the playlist id record if it does not exist.
        database = self.openConnection()
        if database.execute("SELECT PlaylistId FROM PlaylistIds WHERE PlaylistId = ? LIMIT 1;", [playlistId]).fetchone() is None:
            database.execute("INSERT INTO PlaylistIds VALUES (?,?,'[]');", [playlistId, datetime.fromisocalendar(1970, 1, 1).isoformat()])

        # Update the record if the cached value is too old.
        currentTime = datetime.now()
        lastFetchTime = datetime.fromisoformat(database.execute("SELECT FetchTime FROM PlaylistIds WHERE PlaylistId = ? LIMIT 1;", [playlistId]).fetchone()[0])
        if (currentTime - lastFetchTime).total_seconds() > self.playlistCacheTimeSeconds:
            print("Fetching updated playlist ids for " + playlistId)

            # Get the video ids.
            videoIds = []
            pageToken = None
            while True:
                # Build the URL.
                url = "https://youtube.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId=" + playlistId + "&key=" + self.youTubeApiKey
                if pageToken is not None:
                    url += "&pageToken=" + pageToken

                # Add the video ids.
                pageDataResponse = requests.get(url)
                pageData = pageDataResponse.json()
                if pageDataResponse.status_code == 403 and "quotaExceeded" in pageDataResponse.text:
                    raise ConnectionError("YouTube API quota exceeded.")
                if "items" not in pageData.keys():
                    break
                for item in pageData["items"]:
                    videoIds.append(item["snippet"]["resourceId"]["videoId"])

                # Stop the loop if there is no next page or going through pages is ignored.
                if "nextPageToken" not in pageData.keys():
                    break

                # Set the page token for the next loop.
                pageToken = pageData["nextPageToken"]

            # Store the video ids.
            database.execute("UPDATE PlaylistIds SET FetchTime = ?, VideoIds = ? WHERE PlaylistId = ?;", [currentTime.isoformat(), json.dumps(videoIds), playlistId])
            database.commit()

        # Return the playlist video ids.
        videoIds = json.loads(database.execute("SELECT VideoIds FROM PlaylistIds WHERE PlaylistId = ? LIMIT 1;", [playlistId]).fetchone()[0])
        database.close()
        return videoIds

    def addNewPlaylistVideoIdsQuick(self, playlistId: str):
        """Sends a single request for the latest videos of a playlist and stores them.
        This is only intended for quick, frequent updates.

        :param playlistId: Playlist id to update.
        """

        # Get the existing playlist ids.
        # The listing function respects caching.
        videoIds = self.listPlaylistVideoIds(playlistId)

        # Get the first 50 videos in the playlist and add them to the list.
        print("Fetching first 50 video ids for " + playlistId)
        url = "https://youtube.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId=" + playlistId + "&key=" + self.youTubeApiKey
        pageDataResponse = requests.get(url)
        pageData = pageDataResponse.json()
        if pageDataResponse.status_code == 403 and "quotaExceeded" in pageDataResponse.text:
            raise ConnectionError("YouTube API quota exceeded.")
        pageData["items"].reverse()
        for item in pageData["items"]:
            videoId = item["snippet"]["resourceId"]["videoId"]
            if videoId not in videoIds:
                videoIds.insert(0, videoId)

        # Store the video ids.
        database = self.openConnection()
        database.execute("UPDATE PlaylistIds SET VideoIds = ? WHERE PlaylistId = ?;", [json.dumps(videoIds), playlistId])
        database.commit()
        database.close()

    def addVideoIdToPlaylistCache(self, playlistId: str, videoId: str) -> None:
        """Adds a video as part of the cached playlist.

        :param playlistId: Id of the playlist to add to.
        :param videoId: Id of the video to add.
        """

        playlistIds = self.listPlaylistVideoIds(playlistId)
        playlistIds.append(videoId)
        database = self.openConnection()
        database.execute("UPDATE PlaylistIds SET VideoIds = ? WHERE PlaylistId = ?;", [json.dumps(playlistIds), playlistId])
        database.commit()
        database.close()

    def updateVideosIds(self, updateMethod, videoIds: List[str]) -> None:
        """Updates a list of videos in parallel.

        :param updateMethod: Update method to call.
        :param videoIds: Video ids to update.
        """

        pool = ThreadPool(10)
        pool.map(updateMethod, videoIds)
        pool.close()
        pool.join()

    def updateCachedPlaylistVideos(self, playlistId: str, updateMethod: str) -> None:
        """Updates the videos of a playlist.

        :param playlistId: Id of the playlist to update.
        :param updateMethod: Method to update the playlist videos ("ROLLING" or "OLD").
        """

        playlistVideoIds = self.listPlaylistVideoIds(playlistId)
        if updateMethod == "OLD":
            # Updates all the videos in the playlist that are old.
            print("Updating all videos if they haven't been fetched recently.")
            self.updateVideosIds(self.getVideo, playlistVideoIds)
        elif updateMethod == "ROLLING":
            # Get the latest videos.
            print("Updating videos using a rolling method.")
            videoIdsToUpdate = []
            for i in range(0, min(self.rollingUpdateMaxLatestVideos, len(playlistVideoIds))):
                videoIdsToUpdate.append(playlistVideoIds[i])

            # Get the videos that haven't been set up.
            uninitializedVideoThreshold = datetime.fromisocalendar(1980, 1, 1)
            pendingVideosToCheck = []
            for videoId in playlistVideoIds:
                if videoId not in videoIdsToUpdate:
                    lastUpdateTime = self.getVideoCacheTime(videoId)
                    if lastUpdateTime < uninitializedVideoThreshold:
                        videoIdsToUpdate.append(videoId)
                    else:
                        pendingVideosToCheck.append({
                            "videoId": videoId,
                            "lastUpdateTime": lastUpdateTime,
                        })

            # Sort the pending videos by time.
            pendingVideosToCheck = sorted(pendingVideosToCheck, key=lambda d: d["lastUpdateTime"])
            remainingOldVideos = self.rollingUpdateMaxOldestVideos
            for pendingVideo in pendingVideosToCheck:
                if pendingVideo["videoId"] not in videoIdsToUpdate:
                    videoIdsToUpdate.append(pendingVideo["videoId"])
                    remainingOldVideos += -1
                    if remainingOldVideos <= 0:
                        break

            # Update the videos.
            print("Updating " + str(len(videoIdsToUpdate)) + " videos.")
            self.updateVideosIds(self.updateCachedVideo, videoIdsToUpdate)