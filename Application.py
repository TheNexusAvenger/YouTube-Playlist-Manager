"""
TheNexusAvenger

Runs the tasks in a loop for the application.
"""

import time
from datetime import datetime
from YouTube.YouTubeTasks import YouTubeTasks

if __name__ == '__main__':
    # Create the tasks.
    tasks = YouTubeTasks()

    # Run the loop.
    while True:
        print("Performing actions for " + str(datetime.now()))
        tasks.performActions()
        time.sleep(tasks.configuration["Application"]["TaskLoopDelay"] * 60)
