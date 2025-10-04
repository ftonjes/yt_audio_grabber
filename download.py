"""

    Download best quality audio files from YouTube videos using the Youtube URL.

"""
import re
import requests
import imageio_ffmpeg
import subprocess as sp
import os
from pytubefix import YouTube
from mutagen.mp4 import MP4, MP4Cover
from io import BytesIO
from pprint import pprint

requests.packages.urllib3.disable_warnings()

def extract_audio(original_file, file_to_write, start_position=0, end_position=1000000):

    """

    :param original_file: Name of file to extract audio from
    :param file_to_write: Name of file to write extracted audio to
    :param start_position: Start time in milliseconds
    :param end_position: End time in milliseconds
    :return: True
    """

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    sp.run(
        [
            ffmpeg_path,
            '-ss', str(start_position / 1000),
            '-to', str(end_position / 1000),
            '-i', original_file,
            file_to_write,
            '-y'
        ],
        stderr=sp.DEVNULL,
        stdout=sp.DEVNULL)

    return True


# Configuration
list_file = '/Volumes/Data/Projects/yt_audio_grabber/playlist.txt'  # Text file containing one YouTube URL per line
audio_save_location = '/Volumes/Data/Projects/yt_audio_grabber/music/'   # Location where to save the processed tracks
image_save_location = '/Volumes/Data/Projects/yt_audio_grabber/artwork/'   # Location where to save the downloaded album artwork
keep_compilation_track = True

# Check if save locations exist and create if required:
if not os.path.exists(audio_save_location):
    os.makedirs(audio_save_location)
if image_save_location is not None:
    if not os.path.exists(image_save_location):
        os.makedirs(image_save_location)

# Open list of YouTube URLs:
with open(list_file) as f:
    videos = f.read().split('\n')

# Iterate through and process URLs in file:
for video in videos:

    if re.search(r'^#', video) or video == '':
        continue
    if video == ':STOP:':
        print("STOP FOUND!")
        exit()
    # Download file from YouTube:
    tmp = re.search(r'(.*?)(https://.*?)&?$', video)
    if tmp:

        # Download HTML from YouTube so track info can be found in the code:
        url = tmp.group(2)
        wp = requests.get(url, verify=False)

        # Get title of song:
        name = tmp.group(1).strip()
        if len(tmp.group(1)) == 0:
            tmp = re.search(
                r'{"playerOverlayVideoDetailsRenderer":{"title":{"simpleText":"(.*?)"},"subtitle"', wp.text)
            if tmp:
                print(f"Video title: '{tmp.group(1)}'")
                name = tmp.group(1).strip()

        # Get Thumbnail image URL
        thumbnail_url = False
        tmp = re.search(r'"thumbnailUrl":"(https://.*?maxres.*?)"', wp.text)
        if tmp:
            thumbnail_url = tmp.group(1)

        # Clean the name so it looks cleaner (including phrases or single characters)
        clean = [
            '/', ' (Official Music Video)', ' (Official Video)', 'Official Video',
            ' [Official Music Video]', ' [Official Music Video]', ' [FULL ALBUM]', ' (FULL ALBUM)',
            '  [FULL ALBUM - OUT NOW]', ' [FULL SET]',' (FULL SET)', ' FULL SET', ' 4K',
            ' [official music video]', '[Music Video]',
        ]

        for item in clean:
            name = name.replace(item, '').strip()
        name = name.replace('|', '-').replace('｜', ' - ').replace(':', ',').replace(
            '\\u0026', '&').replace(' VOL. ', ' VOL ').replace('  ', ' ')
        name = re.sub(r"\(VOL. (\d+)\)", 'VOL \\1', name)  # Remove full-stop from 'VOL. 1' ('VOL 1')

        # Check if the video has multiple tracks in one file and create a playlist with start/end times incl. track no
        #   and links to add to the comments (via tags).
        playlist = {}
        tmp = re.compile(r'({"chapterRenderer":{.*?}})', re.MULTILINE | re.DOTALL)
        for index, match in enumerate(re.findall(tmp, wp.text)):

            title = 'Unknown'
            tmp = re.search(r'{"title":{"simpleText":"(.*?)"}', match)
            if tmp:
                title = tmp.group(1).replace('|', '-').replace('｜', '-').replace(
                    ':', '').replace('\\u0026', '&')

            track_start = 0
            tmp = re.search(r',"timeRangeStartMillis":(\d+),', match)
            if tmp:
                track_start = int(tmp.group(1))

            # Remove numbering from the start of a track
            rn = re.search(rf'^(\d+(\.)?)', title)
            if rn:
                title = title.replace(rn.group(1), '', 1).replace('\\u0026', '&').strip()

            title = re.sub(r'^\.', '', title)

            playlist[index] = {"number": index + 1, 'title': title, 'msf': track_start}
            if index > 0:
                playlist[index - 1]['mst'] = track_start
                playlist[index]['track_link'] = url + f"&t={str(int(track_start/1000))}"
            else:
                playlist[index]['track_link'] = url

        # Set the last songs ending time:
        if len(playlist) > 0:
            playlist[len(playlist) - 1]['mst'] = 1000000000

        # Download track and prepare directories if a compilation video is found:
        yt = YouTube(url)
        stream = yt.streams.filter(mime_type='audio/mp4').order_by('abr').desc().first()
        if len(playlist) > 0:
            if not os.path.exists(f"{audio_save_location}{name}"):
                os.makedirs(f"{audio_save_location}{name}")
            if image_save_location is not None:
                if not os.path.exists(f"{image_save_location}{name}"):
                    os.makedirs(f"{image_save_location}{name}")
        output_file = f"{audio_save_location}{name}.mp4"
        stream.download(output_path=audio_save_location, filename=f"{name}.mp4")

        # Split file into multiple if required:
        if len(playlist) > 0:

            for items in playlist:

                item = playlist[items]

                # Extract audio for this playlist item:
                audio_to_write = f"{audio_save_location}{name}/{item['title']}.mp4"
                image_to_write = f"{image_save_location}{name}/{item['title']}.jpg"
                extract_audio(
                    original_file=output_file,
                    file_to_write=audio_to_write,
                    start_position=item['msf'],
                    end_position=item['mst']
                )

                # Execute 'sacad' via shell to obtain the best quality image from various sources. The sacad package
                #   has a shell version which appears to work better than using the module itself
                #   (asyncio complications!). If track title contains ' - ' we assume the text to the left of this is
                #   the Artist details and to the right is the name of the track.
                tmp = re.search(r'^(.*?) - (.*)$', item['title'])
                if tmp:

                    artist_brackets = re.search(r'^(.*)\(', tmp.group(1))
                    if artist_brackets:
                        clean_artist = artist_brackets.group(1)
                    else:
                        clean_artist = tmp.group(1)

                    title_brackets = re.search(r'^(.*)\(', tmp.group(2))
                    if title_brackets:
                        clean_title = title_brackets.group(1)
                    else:
                        clean_title = tmp.group(2)

                    cmd_to_run = (
                        f'sacad -t 100 "{clean_artist}" "{clean_title}" 1600 '
                        f'"{image_save_location}{name}/{item["title"]}.jpg" -v quiet')
                else:
                    cmd_to_run = (
                        f'sacad -t 100 "{item["title"]}" "{name}" 1600 "{image_save_location}{name}{item["title"]}.jpg'
                        f'" -v quiet')

                os.system(cmd_to_run)

                # Now exit the downloaded MP4 song and add some tags and album artwork!
                MP4File = MP4(audio_to_write)
                try:
                    with open(f'{image_save_location}{name}/{item["title"]}.jpg', 'rb') as f:
                        album_art = MP4Cover(f.read(), imageformat='MP4Cover.FORMAT_JPEG')
                except FileNotFoundError:
                    img_file_found = False
                    pass
                else:
                    # Tag list: https://mutagen.readthedocs.io/en/latest/api/mp4.html
                    MP4File.tags['covr'] = [bytes(album_art)]
                    img_file_found = True

                tmp = re.search(f'^(.*?) - (.*?)$', item['title'])
                if tmp:
                    MP4File.tags['\xa9nam'] = tmp.group(2)
                    MP4File.tags['\xa9ART'] = tmp.group(1)
                else:
                    MP4File.tags['\xa9nam'] = item['title']

                MP4File.tags['trkn'] = [(int(item['number']), len(playlist))]
                MP4File.tags['disk'] = [(1, 1)]
                MP4File.tags['\xa9cmt'] = item['track_link']
                MP4File.tags['\xa9alb'] = name
                MP4File.tags['cpil'] = True
                MP4File.tags['pgap'] = True
                MP4File.save(audio_to_write)
                print(f"Created track {int(item['number'])} of {len(playlist)}: '{audio_to_write}'.")

        else:

            # Execute 'sacad' via shell to obtain the best quality image from various sources. The sacad package
            #   has a shell version which appears to work better than using the module itself
            #   (asyncio complications!). If track title contains ' - ' we assume the text to the left of this is
            #   the Artist details and to the right is the name of the track.
            tmp = re.search(r'^(.*?) - (.*)$', name)
            if tmp:
                cmd_to_run = (
                    f'sacad "{tmp.group(1)}" "{tmp.group(2)}" 900 "{image_save_location}{name}.jpg" -v quiet')
            else:
                cmd_to_run = (
                    f'sacad "{name}" "{name}" 900 "{image_save_location}{name}.jpg" -v quiet')

            os.system(cmd_to_run)

            if os.path.isfile(f"{image_save_location}{name}.jpg"):
                print('Found it')
            else:
                img_data = requests.get(thumbnail_url).content
                with open(f"{image_save_location}{name}.jpg", "wb") as f:
                    f.write(img_data)

            image_to_write = f"{image_save_location}{name}.jpg"

            # Now add some tags and album artwork!
            MP4File = MP4(output_file)
            if not MP4File.tags:
                MP4File.add_tags()

            try:
                with open(image_to_write, 'rb') as f:
                    album_art = MP4Cover(f.read(), imageformat='MP4Cover.FORMAT_JPEG')
            except FileNotFoundError:
                img_file_found = False
                # If we don't find an image, use the thumbnail from youtube
                pass
            else:
                # Tag list: https://mutagen.readthedocs.io/en/latest/api/mp4.html
                MP4File.tags['covr'] = [bytes(album_art)]
                img_file_found = True

            tmp = re.search(f'^(.*?) - (.*?)$', name)
            if tmp:
                MP4File.tags['\xa9nam'] = tmp.group(2)
                MP4File.tags['\xa9ART'] = tmp.group(1)
            else:
                MP4File.tags['\xa9nam'] = name

            MP4File.tags['\xa9cmt'] = url
            MP4File.save(output_file)
            print(f"Updated track '{output_file}'.")
