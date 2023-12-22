"""
TheNexusAvenger

Paths to files.
"""

import os

dataPath = os.getenv("DATA_PATH")
if dataPath is None:
    dataPath = os.path.realpath(os.path.join(__file__, ".."))
if not os.path.exists(dataPath):
    os.makedirs(dataPath)

configurationPath = os.path.join(dataPath, "configuration.json")
reportsPath = os.path.join(dataPath, "reports")
cacheDatabasePath = os.path.join(dataPath, "YouTubeCache.sqlite")
clientSecretPath = os.path.join(dataPath, "client_secret.json")
refreshTokenPath = os.path.join(dataPath, "refresh_token.txt")
