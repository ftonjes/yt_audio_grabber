# Youtube Audio Grabber

A simple script to download Youtube video audio.

What you need before running this script:

Near line 46 you will see:

```
# Configuration
list_file = 'C:\\Users\\<Username>\\Desktop\\playlist.txt'  # Text file containing one YouTube URL per line
audio_save_location = 'H:\\YT\\Music\\'   # Location where to save the processed tracks
image_save_location = 'H:\\YT\\Artwork\\'   # Location where to save the downloaded album artwork
keep_compilation_track = True
```

1. Edit these values as required.

    `list_file` should contain a line for each youtube video you wish you extract audio for. This is typically in the format:

```
Name of the video/audio                 https://www.youtube.com/watch?v=youtubeCoDe
```

  * The first section is what the downloader will name the 'Album' as. Any white space before and after is stripped away.
  * The 'http' section should contain the URL of the video (not including any other paramaters!)

    `audio_save_location` and `image_save_location` are locations on your device where files are to be saved.

2. Ensure the correct packages are installed (requirements.txt)

`NOTE`: The sacad python module didn't work well on my machine so I just broke the rule and did the 'os.system' thing, i.e.: rand the command via shell! (I know right!) 

3. The script does the following:
  * download the Youtube video
  * Checks to see if there is a 'playlist' (multiple tracks)
  * If there are no timestamped tracks, only the downloaded file will have it's audio extracted and saved (always uses the highest quality audio encoded in the video).
  * If there are multiple tracks:
    * The script will break the audio into smaller tracks (as per the time stamps),
    * Each individual track will have it's name checked and 'cleaned' (removes unwanted text from titles, etc)
    * The titles are then searched for any image art based on the tracks name
    * Tag info is updated for the audio file and image art embedded.
    * Files and image art are placed in the folders configured.

The script is very crude and works for what I need it to - so feel free to modify it as needed.

I found some really basic code on github that I could use to download video files from conferences so I figured out how to extract the audio so I could listen to them in the car.
I then wanted to see how far I could go in terms of automating the splitting of file, tagging and downloading of image art was the last challenge!

Python is amazing!

Hope this helps someone!

Happy tinkering!
