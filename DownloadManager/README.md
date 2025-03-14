# Download Manager - video downloader and indexer

## How to Install?

### 1. Download FFmpeg if you don't have it installed already

1a. Go to this website: https://www.ffmpeg.org/download.html  
1b. Choose the appropriate version for your operating system (Windows, macOS, or Linux). Version for Windows can be found on this site: https://www.gyan.dev/ffmpeg/builds/.
1c. Choose the -full version of the build and download it
1d. Extract the downloaded file to a folder on your system.  
1e. Add the FFmpeg binary to your system's PATH environment variable. In simpler words:
- look for a folder named "bin" with a file named "ffmpeg.exe" inside it,
- copy the path to the file (path should end with "\bin"),
- go to your system environment variables (look for "Edit the system environment variables"),
- look for one named "PATH" or "Path" and choose it,
- click "Edit",
- click "New",
- paste the copied path and click "OK" three times.

1f. Open Command Line (CMD for Windows) and type
```bash
  ffmpeg --version
```
If it recognizes the command, you have installed FFmpeg successfully. Remember to open a new CMD window if you have opened one before changing the "Path" variable.

### 2. Download Google Chrome browser if you don't have it installed already

### 3. Download the zip folder from this repository and extract it
The folder is named "DownloadManager.zip"

### 4. FOR LATER RELEASES, OMIT NOW - Download the correct Chrome driver
**If you are using 64-bit Windows 11, you can skip this step.** The correct driver is already included in the downloaded folder.  
If not, download the correct driver from this site: https://googlechromelabs.github.io/chrome-for-testing/#stable and replace the chromedriver.exe with the downloaded one (also name it "chromedriver.exe").
To download, choose the correct STABLE version, copy the link and paste it into browser. Later extract and move the driver to the DownloadManager folder, replacing the already existing driver.

### 5. Check if you have Python3 (at least 3.7 or higher, best 3.12) installed
Most new PCs have it installed by default. Open Command Line and type
```bash
python --version
```
If it recognizes the command and displays text like "Python 3.12.6", you are good to go. Otherwise, install the correct Python version - there are plenty of guides online. Remember to install at least Python 3.7, best if you choose the latest release.
### 5. Install required Python packages
#### Option A: Easy set-up on Windows
Run the file called "installer.bat"
#### Option B
Open Command Line, navigate inside the "DownloadManager" folder. Type:
   ```bash
   pip install -r requirements.txt
   ```


## How to Use?
### Changing the configuration
Inside the "DownloadManager" folder, there is a "config" folder and inside it a file called "downloader_manager.ini". To edit it, open it with any text editor (for example Notepad on Windows).  
Inside it are several properties:
#### Indexing
- index_file_name: what will the created index file be called. Default is "index".
- indexing_format: what will be the index for each video.  
  Placeholders in square brackets ([]) will be replaced by correct information for each video.  
  Default format is "[DATE]: [URL] - [TITLE] - Created by: [ARTIST_LIST]"
  - [DATE] → current date in ISO format (YYYY-MM-DD)
  - [ARTIST_LIST] → a semicolon separated list of video artists or "Unknown" if no information could be obtained.
  - [URL] → link to the video
  - [TITLE] → proper title of the video extracted from the video information or webpage, not URL
  - [PLATFORM] → platform from which the video was downloaded, like YouTube
Playlists are indexed as: "PLAYLIST: [PLATFORM]: [PLAYLIST_URL] - [PLAYLIST_TITLE]", with all playlist videos indexed underneath according to chosen format.
#### Downloading
- video_only: if true, only download video without audio
- max_download_quality: videos will be downloaded in the given quality. If a video does not exist in the chosen quality, the next best existing quality will be downloaded. Default is 3, which means 1080p (Full HD) quality.  
  -1 → audio only, no video, 0 → 144p, 1 → 240p, 2 → 360p, 3 → 480p, 4 → 720p, 5 → 1080p, 6 → 4K
- max_audio_quality: audio will be downloaded in the given quality (with or without video). If a video does not exist in the chosen quality, the next best existing quality will be downloaded. Default is 2, which is 128kbps in Opus encoding.    
  0 → 64kbps, 1 → 96kbps, 2 → 128kbps, 3 → 160kbps
- max_download_size: videos above the given limit will have their quality lowered or not be downloaded at all. This property may not work correctly. Default is -1, which means no limit on size.
#### Encoding
- encoding_standard: decides about the speed and quality of video compression. Slower means files will take less size but compression will take more time.  
  0 → faster, 1 → fast, 2 → medium, 3 → slow, 4 → slower
- crf: decides about video quality after encoding, higher CRF value (lower index) means that videos will be of worse quality but encoding will be faster  
  0 → 32, 1 → 28, 2 → 23, 3 → 21, 4 → 18
- use_h265: whether to use h264 or h265 codec for videos. H265 is better in all aspects, but encoding takes longer and is not supported on older hardware and may require third party software to display (like VLC Player) on Windows 10  
  true → use h265 codec, false → use older h264 instead
### Running the application
#### Option A: Easy start on Windows
Run the "DownloadManager.bat" file.
#### Option B
Open Command Line and navigate one level above the "DownloadManager" folder. Type:
   ```bash
    python -m DownloadManager 
   ```
### Using the application
- Path to the save directory: the videos and index file will be saved under the entered path. New folders/files will be created if needed.
- URL to video: Go to the website, choose a video and copy the video URL in the search bar (all of it, with the https and such). Do not bother to choose the video quality beforehand, the only thing that matters is the quality in the "download_manager.ini" configuration file.  
  Multiple URLs can be queued, and each video will be downloaded, processed and indexed. This means that you can queue up a few videos and just leave it running in the background.
- Entering a blank URL (clicking Enter) ends the URL collection process and starts the downloading part.
- To cancel any downloading or processing, you can either close the Command Line window or press CTRL+C inside the Command Line.

### How does it work under the hood?
All valid URLs are queued to be downloaded.
Using yt-dlp library (https://github.com/yt-dlp - many thanks to them for the awesome tool), a video gets downloaded in the appropriate quality. Downloading failure skips the current URL and moves to the next one in the queue.
Then using FFmpeg the video gets converted and compressed from .mp4 or .webm to .mkv with chosen codec and audio encoding, further customized by other attributes that you may configure.
(a 200MB video can get reduced to 50MB without losing any quality of image or sound). This process, however, can take quite some time if your computer has a bad graphics card, so be patient. When it finishes, the .temp versions of files will be deleted, leaving only the desired one.
After the downloaded video has been converted and compressed, it's time for indexing.  
The given indexing format (from the configuration file) is appended to a new line in the index file, with all placeholder values replaced. If there is an ARTIST_LIST placeholder in the indexing format, the script attempts to obtain their names.  
If artists are not present in extracted video information (on YouTube they always are), a hidden lightweight version of Google Chrome browser is silently created and opened.
It attempts to visit the video under the URL and download the HTML page content after the video hosting server has delivered it (may take a few seconds).
If it succeeds, the artists names are extracted from the HTML content. If not, they are replaced with "Unknown". The browser driver is closed after it's no longer needed.  
Finally, the correct index for the video is saved to the index file, and the program moves to the next URL in the queue.  
When all URLs have been processed, the index file is saved and the program finishes its work.
## How to Remove
To remove the script, deleting the "DownloadManager" folder is enough. To remove FFmpeg, Google Chrome or Python, look for their respective removal guides - although I would advise against it, apart from Google Chrome, they are great tools to work with.