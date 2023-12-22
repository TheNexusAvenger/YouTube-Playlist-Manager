"""
TheNexusAvenger

Main script for the YouTube playlist manager.
"""
from YouTube.YouTubeTasks import YouTubeTasks


if __name__ == '__main__':
    YouTubeTasks().performActions()
    input("Press enter to close.")
