"""
TheNexusAvenger

Helper for dealing with YouTube OAuth2 APIs.
"""
import re

import requests
import urllib
import json
import os
import Paths
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from YouTube.YouTubeCacheDatabase import YouTubeCacheDatabase

staticYouTubeOAuth2Api = None


class OAuth2Configuration:
    def __init__(self):
        """Creates the OAuth2 configuration.
        """

        # Read the client secret file.
        with open(Paths.clientSecretPath) as file:
            clientSecretData = json.loads(file.read())

        # Store the values.
        self.clientId = clientSecretData["web"]["client_id"]
        self.clientSecret = clientSecretData["web"]["client_secret"]
        self.authorizationUrl = clientSecretData["web"]["auth_uri"]
        self.tokenUrl = clientSecretData["web"]["token_uri"]
        self.redirectUrl = clientSecretData["web"]["redirect_uris"][0]


class OAuth2Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handles a GET request.
        """

        # Parse the URL and handle an OAuth2 token.
        parsedUrl = urlparse(self.path)
        if parsedUrl.path == "/oauth2":
            # Parse the query.
            parameters = {}
            for parameter in parsedUrl.query.split("&"):
                splitParameter = parameter.split("=", 1)
                parameters[splitParameter[0]] = splitParameter[1]

            # Get the code OAuth2 initial code.
            code = urllib.parse.unquote(parameters["code"])

            # Update the stored OAuth2 header.
            try:
                # Send the OAuth2 token request.
                print("OAuth2 complete. Attempting token.")
                oauth2Configuration = OAuth2Configuration()
                response = requests.post("https://oauth2.googleapis.com/token", data={
                    "code": code,
                    "client_id": oauth2Configuration.clientId,
                    "client_secret": oauth2Configuration.clientSecret,
                    "redirect_uri": oauth2Configuration.redirectUrl,
                    "grant_type": "authorization_code",
                }).json()

                # Throw an error if there is no code.
                if "access_token" not in response.keys():
                    if os.path.exists(Paths.refreshTokenPath):
                        os.remove(Paths.refreshTokenPath)
                    raise KeyError("Access token was not found. Response: " + json.dumps(response))
                print("New OAuth2 token created.")

                # Store the tokens.
                staticYouTubeOAuth2Api.oauth2TokenHeader = "Bearer " + response["access_token"]
                with open(Paths.refreshTokenPath, "w") as file:
                    file.write(response["refresh_token"])

                # Stop the server.
                if staticYouTubeOAuth2Api.currentServer is not None:
                    staticYouTubeOAuth2Api.currentServer.server_close()
                    staticYouTubeOAuth2Api.currentServer = None

                # Send the response.
                self.send_response(200)
                self.end_headers()
                self.wfile.write(bytes("OAuth2 complete. The browser tab can be closed.", "utf-8"))
            except KeyError as e:
                # Send the error response.
                self.send_response(500)
                self.end_headers()
                self.wfile.write(bytes("OAuth2 failed.\n" + str(e), "utf-8"))
            return

        # Create the redirect.
        oauth2Configuration = OAuth2Configuration()
        url = oauth2Configuration.authorizationUrl + "?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube&access_type=offline&include_granted_scopes=true&redirect_uri=" + urllib.parse.quote(oauth2Configuration.redirectUrl) + "&response_type=code&client_id=" + urllib.parse.quote(oauth2Configuration.clientId)
        self.send_response(307)
        self.send_header("Location", url)
        self.end_headers()
        self.wfile.write(bytes("Redirecting...", "utf-8"))


class YouTubeOAuth2Api:
    def __init__(self, apiKey: str, youTubeCacheDatabase: YouTubeCacheDatabase):
        """Creates the YouTube OAuth2 API helper.

        :param apiKey: API key for the YouTUbe APIs.
        :param youTubeCacheDatabase: Cache database for the playlists.
        """

        self.apiKey = apiKey
        self.youTubeCacheDatabase = youTubeCacheDatabase
        self.oauth2TokenHeader = None
        self.currentServer = None

    def getAuthorizationHeader(self) -> str:
        """Returns the Authorization header.

        :return: Authorization header to use.
        """

        # Return if there is an OAuth2 token.
        if self.oauth2TokenHeader is not None:
            return self.oauth2TokenHeader

        # Prompt for the new code if the refresh token does not exist.
        if not os.path.exists(Paths.refreshTokenPath) and self.currentServer is None:
            serverPort = re.findall(r":(\d+)", OAuth2Configuration().redirectUrl)[0]
            print("No OAuth2 token ready. A web server has been started to handle the request.")
            print("In a browser, open http://localhost:" + serverPort + " and follow the prompted steps.")
            print("After selecting an account, make sure to select the YouTube channel (labeled Youtube) as opposed to the email account.")
            global staticYouTubeOAuth2Api
            staticYouTubeOAuth2Api = self

            try:
                self.currentServer = HTTPServer(("localhost", int(serverPort)), OAuth2Handler)
                self.currentServer.serve_forever()
            except OSError:
                pass  # Server was closed.

        # Return if there is an OAuth2 token.
        # This second one is required due to the first call setting up and taking down the server.
        if self.oauth2TokenHeader is not None:
            return self.oauth2TokenHeader

        # Send the OAuth2 token request.
        print("Attempting to get OAuth2 code.")
        oauth2Configuration = OAuth2Configuration()
        with open(Paths.refreshTokenPath) as file:
            refreshToken = file.read()
        response = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": oauth2Configuration.clientId,
            "client_secret": oauth2Configuration.clientSecret,
            "refresh_token": refreshToken,
            "grant_type": "refresh_token",
        }).json()

        # Throw an error if there is no code.
        if "access_token" not in response.keys():
            if os.path.exists(Paths.refreshTokenPath):
                os.remove(Paths.refreshTokenPath)
            raise KeyError("Access token was not found. Response: " + json.dumps(response))
        print("New OAuth2 access token created.")

        # Return the header.
        self.oauth2TokenHeader = "Bearer " + response["access_token"]
        return self.oauth2TokenHeader

    def initializeAuthorizationHeader(self) -> str:
        """Initializes the authorization header.

        :return: Authorization header to use.
        """

        try:
            return self.getAuthorizationHeader()
        except:
            print("Authorization failed. Refresh token may be invalid.")
            return self.getAuthorizationHeader()

    def addToPlaylist(self, playlistId: str, videoId: str) -> None:
        """Adds a video to a playlist.

        :param playlistId: Id of the playlist to add to.
        :param videoId: Id of the video to add.
        """

        # Return if the video already exists on the playlist.
        if videoId in self.youTubeCacheDatabase.listPlaylistVideoIds(playlistId):
            return

        # Add the video.
        response = requests.post("https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&key=" + self.apiKey,
            headers={
                "Authorization": self.getAuthorizationHeader()
            }, json={
                "snippet": {
                    "playlistId": playlistId,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": videoId,
                    }
                }
            })

        # Throw an error if the quota was reached.
        if response.status_code == 403 and "quotaExceeded" in response.text:
            raise ConnectionError("YouTube API quota exceeded.")
        elif response.status_code != 200:
            raise RuntimeError("Video not added to playlist (HTTP " + str(response.status_code) + "): " + response.text)

        # Add the video id to the playlist cache.
        print("Added video " + videoId + " to playlist " + playlistId)
        self.youTubeCacheDatabase.addVideoIdToPlaylistCache(playlistId, videoId)
