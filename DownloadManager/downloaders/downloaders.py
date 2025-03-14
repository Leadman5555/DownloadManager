import datetime
from abc import ABC, abstractmethod
import os

import yt_dlp
from yt_dlp import YoutubeDL

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

    def append_playlist_to_index(self, playlist_url: str, playlist_title: str, entries: list[dict[str, str]], creators: list[str], platform: str) -> bool:
        if not self.is_open:
            self.open()
        try:
            self.file.write(f"PLAYLIST: {platform}: {playlist_url} - {playlist_title}:\n")
            for entry, creator in zip(entries, creators):
                self._append_format(entry['url'], entry['title'], [creator], platform, True)
            self.file.write("\n")
            return True
        except TypeError:
            MessageHandler.error("Invalid data type provided for writing.")
        except PermissionError:
            MessageHandler.error("Permission denied: Unable to write to the file.")
        except OSError as e:
            MessageHandler.error(f"OS-related error occurred: {e}")
        return False

    def append_to_index(self, url: str, title: str, artist_list: list[str], platform: str) -> bool:
        if not self.is_open:
            self.open()
        try:
            self._append_format(url, title, artist_list, platform)
            return True
        except TypeError:
            MessageHandler.error("Invalid data type provided for writing.")
        except PermissionError:
            MessageHandler.error("Permission denied: Unable to write to the file.")
        except OSError as e:
            MessageHandler.error(f"OS-related error occurred: {e}")
        return False

    def _append_format(self, url: str, title: str, artist_list: list[str], platform: str, indent: bool = False):
        formatted_index = (self.indexing_format
                           .replace("[URL]", url)
                           .replace("[TITLE]", title)
                           .replace("[PLATFORM]", platform)
                           .replace("[DATE]", self.chosen_date)
                           .replace("[ARTIST_LIST]", ", ".join(artist_list)) + '\n')
        MessageHandler.info(f"Indexing video: {title}...")
        if indent:
            self.file.write(f"\t{formatted_index}")
        else:
            self.file.write(formatted_index)
        MessageHandler.info(f"Indexed video as: {formatted_index}")

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
        self._playlist_info_options = {
            'playlist_items': '1',
            'quiet': True,
            'extract_flat': False
        }

    @abstractmethod
    def get_sample_urls(self) -> list[str]:
        pass

    @abstractmethod
    def download_and_index(self, url_list: list[tuple[str, str, bool]], indexer) -> int:
        pass

    def sanitize_url(self, url: str) -> tuple[str, str, bool] | None:
        if len(url) > len(self.url_scheme) and url.startswith(self.url_scheme):
            return self.trim_params_and_validate(url)
        return None

    @staticmethod
    @abstractmethod
    def validate_video_part(video_part: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def validate_playlist(playlist_part: str) -> bool:
       pass

    @staticmethod
    @abstractmethod
    def get_video_part(url: str, scheme_length: int) -> tuple[str, int]:
        pass

    @staticmethod
    @abstractmethod
    def get_video_and_playlist_parts(url: str, scheme_length: int) -> tuple[str, str, int]:
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

    def trim_params_and_validate(self, url: str) -> tuple[str, str, bool] | None:
        if self.is_playlist(url):
            video_part, playlist_part, trim_index = self.get_video_and_playlist_parts(url, len(self.url_scheme))
            if not self.validate_video_part(video_part): return None
            if not self.validate_playlist(playlist_part): return None
            if trim_index == -1:
                return url, playlist_part, True
            return url[:trim_index], playlist_part, True
        else:
            video_part, trim_index = self.get_video_part(url, len(self.url_scheme))
            if not self.validate_video_part(video_part): return None
            if trim_index == -1:
                return url, video_part, True
            return url[:trim_index], video_part, True

    @abstractmethod
    def is_playlist(self, url: str) -> bool:
        pass

class EmbeddedVideoMetadataDownloader(BaseDownloader, ABC):
    def download_and_index(self, url_list: list[tuple[str, str, bool]], indexer: Indexer = None) -> tuple[int, int]:
        download_success_count: int = 0
        index_success_count: int = 0
        count: int = len(url_list)
        with yt_dlp.YoutubeDL(self._yt_dlp_options) as downloader:
            for url in url_list:
                count -= 1
                if url[2]:
                    with yt_dlp.YoutubeDL(self._playlist_info_options) as playlist_extractor:
                        MessageHandler.info(f"Downloading playlist information {url[1]}...")
                        try:
                            playlist_info = playlist_extractor.extract_info(url[0], download=False)
                            if playlist_info is None:
                                MessageHandler.error(f"Failed to fetch playlist information for {url[1]}. Skipping entire playlist... Items in queue left: {count}.\n")
                                continue
                            playlist_title = playlist_info['title']
                            playlist_count = playlist_info['playlist_count']
                            MessageHandler.info(f"Playlist information fetched for {url[1]}. Playlist title: {playlist_title}. Videos in playlist: {playlist_count}.\n")
                            if playlist_count > 30:
                                MessageHandler.alert(f"Playlist {playlist_title} has {playlist_count} videos. All of them will be downloaded and converted.")
                            playlist_entries = []
                            downloaded_count, index_success_count = self.download_entry(downloader, url, index_success_count, download_success_count, count, playlist_entries)
                            if downloaded_count != 0:
                                download_success_count = downloaded_count
                                MessageHandler.info(f"Indexing {len(playlist_entries)} videos in playlist {playlist_title}...")
                                indexer.append_playlist_to_index(url[0], playlist_title, playlist_entries, [entry['uploader'] for entry in playlist_entries], self.platform)
                        except yt_dlp.DownloadError as e:
                            MessageHandler.error(f"Failed to fetch playlist information for {url[1]}. Reason {e.msg}. Skipping entire playlist... Items in queue left: {count}.\n")
                else:
                    download_success_count, index_success_count = self.download_entry(downloader, url, index_success_count, download_success_count, count, None, indexer)
                    MessageHandler.success(f"Success count: {download_success_count}D and {index_success_count}I of {len(url_list)} entries. Items in queue for {self.platform} left: {count}.\n")
            return download_success_count, index_success_count


    def download_entry(self, downloader: YoutubeDL, url: tuple[str, str, bool], index_success_count: int, download_success_count: int, count: int, playlist_entries: list[str] =None, indexer: Indexer = None) -> tuple[int, int]:
        try:
            MessageHandler.info(f"Attempting to download entry: {url[1]}...")
            info = downloader.extract_info(url[0], download=True)
            if info is None: raise yt_dlp.DownloadError("Failed to fetch entry metadata")
            download_success_count += 1
            MessageHandler.info(f"Downloaded entry: {url[1]}")
            title = info['title']
            uploader = info['uploader']
            if playlist_entries is None and indexer is not None:
                if indexer.append_to_index(url[0], title, [uploader], self.platform):
                    index_success_count += 1
                    MessageHandler.success(f"Downloading and indexing for video {url[1]} complete. Remaining items in queue: {count}")
            else:
                playlist_entries.extend(info['entries'])
                MessageHandler.success(f"Downloading playlist {url[1]} complete. Remaining items in queue: {count}")
        except yt_dlp.DownloadError as e:
            MessageHandler.error(f"Failed to download video: {url[1]}. Reason: {e.msg}. Skipping... Remaining items in queue: {count}.\n")
        finally:
            return download_success_count, index_success_count

    def _add_video_format_setup(self, video_format: str):
        self._yt_dlp_options['format'] = self._yt_dlp_options.get('format',
                                                                  '') + f'bestvideo[height<={video_format}]+bestaudio/best[height<={video_format}]/worst[height>{video_format}]'

class YoutubeDownloader(EmbeddedVideoMetadataDownloader):

    @staticmethod
    def validate_playlist(playlist_part: str) -> bool:
        for char in playlist_part:
            code = ord(char)
            if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122) or code == 45 or code == 95:
                continue
            else:
                return False
        return True

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

    @staticmethod
    def get_video_part(url: str, scheme_length: int) -> tuple[str, int]:
        next_param_index = url.find('&', scheme_length+1)
        if next_param_index == -1:
            return url[scheme_length:], -1
        return url[scheme_length:next_param_index], next_param_index

    @staticmethod
    def get_video_and_playlist_parts(url: str, scheme_length: int) -> tuple[str, str, int]:
        first_param_index = url.find('&', scheme_length+1)
        next_param_index = url.find('&', first_param_index+1)
        return url[scheme_length:first_param_index], url[first_param_index+6:next_param_index], next_param_index

    @property
    def url_scheme(self):
        return 'https://www.youtube.com/watch?v='

    @property
    def platform(self):
        return YOUTUBE_KEY

    def get_sample_urls(self) -> list[str]:
        return [
            f'{self.url_scheme}[VIDEO_CODE]',
            f'{self.url_scheme}[VIDEO_CODE]&list=[PLAYLIST_CODE]'
        ]

    def is_playlist(self, url: str) -> bool:
        return '&list=' in url[len(self.url_scheme):]

class TwitchDownloader(EmbeddedVideoMetadataDownloader):

    @staticmethod
    def validate_video_part(video_part: str) -> bool:
        if len(video_part) != 10: return False
        for char in video_part:
            if 48 <= ord(char) <= 57:
                continue
            else:
                return False
        return True

    @staticmethod
    def validate_playlist(playlist_part: str) -> bool:
        raise Exception("Twitch does not support playlists")

    @staticmethod
    def get_video_part(url: str, scheme_length: int) -> tuple[str, int]:
        next_param_index = min(url.find('/', scheme_length+1), url.find('?', scheme_length+1))
        if next_param_index == -1:
            return url[scheme_length:], -1
        return url[scheme_length:next_param_index], next_param_index

    @staticmethod
    def get_video_and_playlist_parts(url: str, scheme_length: int) -> tuple[str, str, int]:
        raise Exception("Twitch does not support playlists")

    @property
    def url_scheme(self):
        return 'https://www.twitch.tv/videos/'

    @property
    def platform(self):
        return TWITCH_KEY

    def get_sample_urls(self) -> list[str]:
        return [f'{self.url_scheme}[VIDEO_CODE]']

    def is_playlist(self, url: str) -> bool:
        return False

YOUTUBE_KEY = 'Youtube'
YOUTUBE_MATCH = 'youtube'
TWITCH_KEY = 'Twitch'
TWITCH_MATCH = 'twitch'

def match_url_to_platform(url: str) -> str | None:
    if (len(url)) < 12: return None
    sub_ulr = url[12:] #https://www.
    if sub_ulr.startswith(YOUTUBE_MATCH):
            return YOUTUBE_KEY
    elif sub_ulr.startswith(TWITCH_MATCH):
            return TWITCH_KEY
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
                path_to_save_location),
        TWITCH_KEY:
            TwitchDownloader(
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
