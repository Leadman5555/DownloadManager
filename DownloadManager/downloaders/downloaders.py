import datetime
from abc import ABC, abstractmethod
import os

import yt_dlp

from DownloadManager.message_handler import MessageHandler


class Indexer:

    def __init__(self,
             path_to_index_file: str,
             indexing_format: str,
             chosen_date: str = None):
        self.path_to_index_file = path_to_index_file
        self.indexing_format = indexing_format
        if chosen_date is not None: self.chosen_date = chosen_date
        else: self.chosen_date = str(datetime.date.today())
        self.is_open = False
        self.file = None

    def close_and_configure(self, path_to_index_file: str, indexing_format: str, chosen_date: str = None):
        self.close()
        self.path_to_index_file = path_to_index_file
        self.indexing_format = indexing_format
        if chosen_date is not None: self.chosen_date = chosen_date

    def open(self):
        if self.is_open:
            return
        self.is_open = True
        try:
            self.file = open(self.path_to_index_file, 'a')
        except FileNotFoundError:
            MessageHandler.error("The file or directory does not exist.")
        except PermissionError:
            MessageHandler.error("Permission denied: Unable to write to the file.")
        except IsADirectoryError:
            MessageHandler.error("Cannot open a directory as a file.")
        except OSError as e:
            MessageHandler.error(f"OS-related error occurred: {e}")
        except TypeError:
            MessageHandler.error("Invalid data type provided for writing.")

    def close(self):
        if self.is_open:
            self.file.close()
            self.is_open = False
            self.file = None

    def append_to_index(self, url: str, title: str, artist_list: list[str], platform: str) -> bool:
        if not self.is_open:
            self.open()
        formatted_index = (self.indexing_format
                           .replace("[URL]", url)
                           .replace("[TITLE]", title)
                           .replace("[PLATFORM]", platform)
                           .replace("[DATE]", self.chosen_date)
                           .replace("[ARTIST_LIST]", ", ".join(artist_list)) + '\n')
        MessageHandler.info(f"Indexing video: {title}...")
        try:
            self.file.write(formatted_index)
            MessageHandler.info(f"Indexed video as: {formatted_index}")
            return True
        except TypeError:
            MessageHandler.error("Invalid data type provided for writing.")
        except PermissionError:
            MessageHandler.error("Permission denied: Unable to write to the file.")
        except OSError as e:
            MessageHandler.error(f"OS-related error occurred: {e}")
        return False

class BaseDownloader(ABC):
    @property
    @abstractmethod
    def platform(self):
        pass

    @property
    @abstractmethod
    def url_scheme(self):
        pass

    def __hash__(self):
        return hash(self.platform)

    def __eq__(self, other):
        if not isinstance(other, BaseDownloader): return False
        return self.platform == other.platform

    def __init__(self,
                 should_log_everything: bool,
                 logger,
                 task_finished_hook,
                 video_only: bool,
                 crf: str,
                 encoding_standard: str,
                 use_h265: bool,
                 max_video_quality: str | None,
                 max_audio_quality: str,
                 max_file_size: str | None,
                 path_to_save_location: str):
        self._yt_dlp_options = {
            'verbose': should_log_everything,
            'playliststart': 1,
            'prefer_ffmpeg': True,
            'writesubtitles': False,
            'ignoreerrors': True,
            'fragment_retries': 5,
            'retries': 3,
            'extract_flat': 'discard_in_playlist',
            'logger': logger,
            'progress_hooks': [task_finished_hook],
        }
        self._add_save_location(path_to_save_location)
        if video_only:
            self._change_to_video_only_conversion_setup(use_h265, crf, encoding_standard)
        else:
            if max_video_quality is None:
                self._change_to_audio_only_conversion_setup(max_audio_quality)
            else:
                self._change_to_default_conversion_setup(use_h265, crf, encoding_standard, max_audio_quality)
                self._add_video_format_setup(max_video_quality)
        if max_file_size is not None: self._add_max_file_size_setup(max_file_size)

    @abstractmethod
    def get_sample_url(self) -> str:
        pass

    @abstractmethod
    def download_and_index(self, url_list: list[tuple[str, str]], indexer) -> int:
        pass

    @abstractmethod
    def sanitize_url(self, url: str) -> tuple[str, str] | None:
        pass

    @staticmethod
    @abstractmethod
    def validate_video_part(video_part: str) -> bool:
        pass
    
    def _add_save_location(self, path_to_save_location: str):
        self._yt_dlp_options['outtmpl'] = os.path.join(path_to_save_location, "%(title)s.%(ext)s")

    def _add_max_file_size_setup(self, max_file_size: str):
        self._yt_dlp_options['format'] = self._yt_dlp_options.get('format', '') + f'[filesize<={max_file_size}M]'

    @abstractmethod
    def _add_video_format_setup(self, video_format: str):
        pass

    def _change_to_default_conversion_setup(self, use_h265: bool, crf: str, encoding_standard: str, audio_format: str):
        self._yt_dlp_options['postprocessors'] = [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mkv',
            }]
        self._yt_dlp_options['postprocessor_args'] = [
            '-c:v', ('libx264' if use_h265 is False else 'libx265'),
            '-c:a', 'libopus',
            '-crf', crf,
            '-b:a', f'{audio_format}k',
            '-preset', encoding_standard,
        ]
        self._yt_dlp_options['merge_output_format'] = 'mkv'

    def _change_to_audio_only_conversion_setup(self, audio_format: str):
        self._yt_dlp_options['postprocessors'] = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': f'{audio_format}',
            }
        ]
        self._yt_dlp_options['format'] = 'bestaudio/best'

    def _change_to_video_only_conversion_setup(self, use_h265: bool, crf: str, encoding_standard: str):
        self._yt_dlp_options['postprocessors'] = [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mkv',
            }]
        self._yt_dlp_options['postprocessor_args'] = [
            '-c:v', 'libx264' if use_h265 is False else 'libx265',
            '-crf', crf,
            '-preset', encoding_standard,
            '-na'
        ]


class YoutubeDownloader(BaseDownloader):

    def download_and_index(self, url_list: list[tuple[str, str]], indexer: Indexer = None) -> tuple[int, int]:
        download_success_count: int = 0
        index_success_count: int = 0
        count: int = len(url_list)
        with yt_dlp.YoutubeDL(self._yt_dlp_options) as downloader:
            for url in url_list:
                count -= 1
                try:
                    MessageHandler.info(f"Attempting to download video: {url[1]}...")
                    info = downloader.extract_info(url[0], download=True)
                    if info is None: raise yt_dlp.DownloadError
                    download_success_count += 1
                    MessageHandler.info(f"Downloaded video: {url[1]}")
                    title = info['title']
                    uploader = info['uploader']
                    if indexer is not None and (indexer.append_to_index(url[0], title, [uploader], self.platform) is True): index_success_count += 1
                    MessageHandler.success(
                          f"Downloading and indexing for complete. Success count: {download_success_count}D and {index_success_count}I of {len(url_list)}. Videos in queue for {self.platform} left: {count}.\n")
                except yt_dlp.DownloadError:
                    MessageHandler.error(f"Failed to download video: {url[1]}. Skipping... Videos in queue left: {count}.\n")
            return download_success_count, index_success_count

    def sanitize_url(self, url: str) -> tuple[str, str] | None:
        scheme_len = len(self.url_scheme)
        if len(url) > scheme_len and url.startswith(self.url_scheme):
            next_param = url.find('&', scheme_len)
            if next_param == -1:
                if not self.validate_video_part(url[scheme_len:]): return None
                return url, url[scheme_len:]
            else:
                video_part = url[scheme_len:next_param]
                if not self.validate_video_part(video_part): return None
                return url[:next_param], video_part
        return None

    @staticmethod
    def validate_video_part(video_part: str) -> bool:
        if len(video_part) != 11: return False
        for char in video_part:
            code = ord(char)
            if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122) or code == 45 or code == 95:
                continue
            else:
                return False
        return True

    def _add_video_format_setup(self, video_format: str):
        self._yt_dlp_options['format'] = self._yt_dlp_options.get('format',
                                                                '') + f'bestvideo[height<={video_format}]+bestaudio/best[height<={video_format}]'
    @property
    def url_scheme(self):
        return 'https://www.youtube.com/watch?v='

    @property
    def platform(self):
        return YOUTUBE_KEY

    def get_sample_url(self) -> str:
        return f'{self.url_scheme}[VIDEO_CODE]'

YOUTUBE_KEY = 'Youtube'
YOUTUBE_MATCH = 'youtube'

def match_url_to_platform(url: str) -> str | None:
    if (len(url)) < 12: return None
    sub_ulr = url[12:] #https://www.
    if sub_ulr.startswith(YOUTUBE_MATCH):
            return YOUTUBE_KEY
    return None


def create_downloaders(should_log_everything: bool,
                       logger,
                       task_finished_hook,
                       video_only: bool,
                       crf: str,
                       encoding_standard: str,
                       use_h265: bool,
                       max_video_quality: str | None,
                       max_audio_quality: str,
                       max_file_size: str | None,
                       path_to_save_location: str) -> dict[str, BaseDownloader]:
    return {
        YOUTUBE_KEY:
            YoutubeDownloader(
                should_log_everything,
                logger,
                task_finished_hook,
                video_only,
                crf,
                encoding_standard,
                use_h265,
                max_video_quality,
                max_audio_quality,
               max_file_size,
                path_to_save_location)
    }
