This requires a lot of setup with Google Cloud. It only needs to be done once.
First, Google Cloud needs to be set up with a Google account. Go to the console (https://console.cloud.google.com/), enter
your region, and accept the terms and conditions.

# Python 3
For any system running this, Python 3 is required with the `requests` library. In a command or terminal after Python
is installed, run one of the following:
- Windows: `python -m pip install requests`
- macOS/Linux: `python3 -m pip install requests`

# Project
On the top-left near the "Google Cloud" logo, there is a dropdown for projects. When there are no projects, you will have
"Select a project". Click the dropdown, which shows a modal window with a list of projects. On the top-right of the modal,
click "New Project". It requires a valid name. Location can be left as "No organization". Click "Create".

The only API that needs to be added is the YouTube Data API v3. On the API page (https://console.cloud.google.com/marketplace/product/google/youtube.googleapis.com),
click "Enable". By default, there is a fairly strict quota of 10,000 request units per day. Adding to a playlist counts
as 50, only 200 videos can be added to playlists a day with no other requests. For normal use, this shouldn't be a
problem. For the setup, this would make it painful - potentially months. Either manual work is required for the backlog
(covered later), or a new quote needs to be requested (https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas,
select "Queries per day", then "Edit Quotas", and "Apply for a higher quota").

# API Key
All requests need an API key. Under Credentials (https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials),
click "Create Credentials" on the right, then "API key". The API key will be presented and should be copied over. It
can be shown again using "Show key" in the list.

# OAuth2
OAuth2 is required for adding videos to playlists because API Keys don't have a way of connecting to accounts. The setup
is much more complex.

## OAuth Consent Screen
OAuth2 requires a consent screen to be configured, but it does not need to be published. Go to the consent screen
configuration (https://console.cloud.google.com/apis/credentials/consent), which has 4 parts, but part 4 is just
a summary.
- In "OAuth consent screen", give it a useful name, select a user support email, and enter an email for developer
  contact information.
- In "Scopes", select "Add or remove scopes". In the window the appears on the right, next to the filter, type "youtube".
  Find the scope `.../auth/youtube`. Click the checkbox next to it, and then "Update" at the bottom. Under
  "Your sensitive scopes", `.../auth/youtube` will appear.
- In "Test Users", click on "Add users" and ender the email of the Google account with the YouTube channel to control.
  There will be no auto-complete. Once done, click "Add".

Once it is done, OAuth2 client ids can be set up. It does not need to be published - that requires a review and is only
needed for public-facing OAuth2 apps.

## OAuth Client ID
Under Credentials (https://console.cloud.google.com/apis/api/youtube.googleapis.com/credentials), click on "Create Credentials"
towards the right, and then "OAuth Client ID". When prompted for the application type, use "Web application". Enter
a useful name, and add "http://localhost:45982/oauth2" under "Authorized redirect URIs". Once created, the client id and
client secret will be shown. These can be ignored in favor of "Download JSON". Download the file and rename it to
"client_secret.json", then move it into the same folder as Main.py.

# Usage
## configuration.json
A JSON file named `configuration.json` is required. When `Main.py` is run, it will create a template that looks like
the following:
```json
{
    "YouTubeApiKey": "YOUTUBE_API_KEY_HERE",
    "Caching": {
        "PlaylistCacheUpdateMethod": "ROLLING",
        "PlaylistCacheTimeSeconds": 720,
        "VideoCacheTimeSeconds": 720,
        "RollingUpdateMaxLatestVideos": 5,
        "RollingUpdateMaxOldestVideos": 5
    },
    "Application": {
        "TaskLoopDelayMinutes": 30
    },
    "SourcePlaylists": [
        "SOURCE_PLAYLIST_ID_HERE"
    ],
    "TargetPlaylists": {
        "#hashtag1": [
            "TARGET_PLAYLIST_ID_HERE"
        ],
        "#hashtag2": [
            "TARGET_PLAYLIST_ID_HERE"
        ]
    }
}
```

The fields are:
- `YouTubeApiKey`: API key obtained from the "API Key" section.
- `Caching`:
  - `PlaylistCacheUpdateMethod`: Method used to update the cache. Must be either `OLD` or `ROLLING`.
  - `PlaylistCacheTime`: How long, in minutes, playlist data from YouTube is cached. This is meant to make quick reruns
    for tests faster and less demanding on the API quota. However, cached results will not pick up on new/removed playlist
    items or title/description changes.
  - `VideoCacheTime`: How long, in minutes, video data from YouTube is cached. This is meant to make quick reruns
    for tests faster and less demanding on the API quota. However, cached results will not pick up on new/removed playlist
    items or title/description changes. *Only used when `PlaylistCacheUpdateMethod` is `OLD`.
  - `RollingUpdateMaxLatestVideos`: Maximum amount of the latest videos to update from the cache. *Only used when
    `PlaylistCacheUpdateMethod` is `ROLLING`.*
  - `RollingUpdateMaxOldestVideos`: Maximum amount of the oldest videos to update from the cache. *Only used when
    `PlaylistCacheUpdateMethod` is `ROLLING`.*
- `Application`:
  - `TaskLoopDelay`: Delay (in minutes) between running the cache updates and playlist additions.
- `SourcePlaylists`: List of public/unlisted playlists to source from. For most use cases, there will be only 1 entry.
- `TargetPlaylists`: Dictionary of keywords to look up with the playlist id(s) they go to.

The following below is an example that sources from 2 playlist (UUplaylist1 and UUplaylist2), and puts videos
titles/descriptions containing "[Release]" in Playlist1 and Playlist2, and titles/descriptions containing "#new"
in Playlist2. **These are case-insensitive, and be careful of aggressive matching (i.e. website.com/thing#new-changes
contains #new).**
```json
{
    "YouTubeApiKey": "YOUTUBE_API_KEY_HERE",
    "Caching": {
        "PlaylistCacheUpdateMethod": "ROLLING",
        "PlaylistCacheTimeSeconds": 720,
        "VideoCacheTimeSeconds": 720,
        "RollingUpdateMaxLatestVideos": 5,
        "RollingUpdateMaxOldestVideos": 5
    },
    "Application": {
        "TaskLoopDelay": 30
    },
    "SourcePlaylists": [
        "UUplaylist1",
        "UUplaylist2",
    ],
    "TargetPlaylists": {
        "[Release]": [
            "Playlist1",
            "Playlist2"
        ],
        "#new": [
            "Playlist2"
        ]
    }
}
```

## Running
### Looping Application (Docker)
To run the looping application in the background, start the application using `docker compose up --build` and stop it
using `docker compose down`.

### CLI
Running the CLI program is done using `Main.py`. In a graphical environment, like Windows, your install may be configured
to run Python scripts by double-clicking. When ran, the script will run and wait for the user to press enter when done.
Running it non-graphically on a schedule, such as crontab, is recommended. Guides on that can be found elsewhere, and
there are many ways to do it.

When the script runs, it will:
- Set up OAuth2.
  - If the refresh token (in `refresh_token.txt`) is invalid or expired, a web server will be created to complete the
    OAuth2 process. When requested, you will need to open a browser on the same device as the script and go to
    http://localhost:45982. It will redirect you to the Google OAuth2 page. Select the Google Account with the YouTube
    account with the target playlists, then select the YouTube account (might be the *second* option). Once complete,
    it will redirect back to localhost and can be closed. The rest of the script will continue.
  - The refresh token stored from the request is long-lasting. The manual login process should need to be done rarely.
- Cache a list of the videos in the playlist needed.
- Cache the title and description of the videos in the playlists.
- Calculate the videos to add, keep, and remove for each target playlist.
- Apply as many additions as possible until the quota limit is reached.
  - **Removals must be done manually.** There is no documentation on how to automate it.
- Create text files in a folder named `reports` that shows any remaining videos to remove or add.
  - Videos to add will show when the quota limit is reached. As many as possible will be completed in the next run.