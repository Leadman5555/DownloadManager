#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp
from colorama import Fore, Style
from datetime import date

CONF_FILE_NAME = "download_manager.ini"
allowed_video_formats = ['6', '5', '4', '3', '2', '1', '0', '-1']
video_format_to_quality: dict[str, str] = {
    '-1': 'audio only',
    '0': '144',
    '1': '240',
    '2': '360',
    '3': '480',
    '4': '720',
    '5': '1080',
    '6': '2160',
}
allowed_audio_format = ['3', '2', '1', '0']
audio_format_to_quality: dict[str, str] = {
    '0': '64',
    '1': '96',
    '2': '128',
    '3': '160',
}
allowed_encoding_standards = ['4', '3', '2', '1', '0']
encoding_standard_to_preset: dict[str, str] = {
    '0': 'faster',
    '1': 'fast',
    '2': 'medium',
    '3': 'slow',
    '4': 'slower',
}
allowed_crf_standards = ['4', '3', '2', '1', '0']
crf_standard_to_value: dict[str, str] = {
    '0': '32',
    '1': '28',
    '2': '23',
    '3': '21',
    '4': '18',
}


def get_video_format_mapping_str() -> str:
    base = ""
    for key in video_format_to_quality:
        base += f"{key}: {video_format_to_quality[key]}"
    return base


def get_audio_format_mapping_str() -> str:
    base = ""
    for key in audio_format_to_quality:
        base += f"{key}: {audio_format_to_quality[key]}"
    return base


class YtDlpLogger:
    def debug(self, msg):
        if msg.startswith('[debug] '):
            self.info(msg[8:])
        else:
            self.info(msg)

    @staticmethod
    def info(msg):
        print(Style.RESET_ALL + msg)

    def warning(self, msg):
        pass

    @staticmethod
    def error(msg):
        print(Fore.RED + msg)


def task_finished_hook(d):
    if d['status'] == 'finished':
        print(Fore.GREEN + 'Done downloading, now converting and compressing, may take a while...\n')


yt_dlp_options: dict = {
    'verbose': True,
    'playliststart': 1,
    'prefer_ffmpeg': True,
    'writesubtitles': False,
    'ignoreerrors': True,
    'fragment_retries': 5,
    'retries': 3,
    'extract_flat': 'discard_in_playlist',
    'logger': YtDlpLogger(),
    'progress_hooks': [task_finished_hook],
}


def change_to_default_conversion_setup(audio_format: str, encoding_standard: str, crf: str, use_h265: bool):
    yt_dlp_options['postprocessors'] = [
        {
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mkv',
        }]
    yt_dlp_options['postprocessor_args'] = [
        '-c:v', ('libx264' if use_h265 is False else 'libx265'),
        '-c:a', 'libopus',
        '-crf', crf_standard_to_value[crf],
        '-b:a', f'{audio_format_to_quality[audio_format]}k',
        '-preset', encoding_standard_to_preset[encoding_standard],
    ]
    yt_dlp_options['merge_output_format'] = 'mkv'


def change_to_audio_only_conversion_setup(audio_format: str):
    yt_dlp_options['postprocessors'] = [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': f'{audio_format_to_quality[audio_format]}',
        }
    ]
    yt_dlp_options['format'] = 'bestaudio/best'


def change_to_video_only_conversion_setup(encoding_standard: str, crf: str, use_h265: bool):
    yt_dlp_options['postprocessors'] = [
        {
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mkv',
        }]
    yt_dlp_options['postprocessor_args'] = [
        '-c:v', 'libx264' if use_h265 is False else 'libx265',
        '-crf', crf_standard_to_value[crf],
        '-preset', encoding_standard_to_preset[encoding_standard],
        '-na'
    ]


def add_video_format_setup(chosen_format: str):
    yt_dlp_options['format'] = yt_dlp_options.get('format',
                                                  '') + f'bestvideo[height<={video_format_to_quality[chosen_format]}]+bestaudio/best[height<={video_format_to_quality[chosen_format]}]'
    # yt_dlp_options['format'] = yt_dlp_options.get('format', '') + f'best[height<={format_to_quality[chosen_format]}]'


def add_max_file_size_setup(max_size: str):
    yt_dlp_options['format'] = yt_dlp_options.get('format', '') + f'[filesize<={max_size}M]'


def add_save_location(path_to_save_location: str):
    yt_dlp_options['outtmpl'] = os.path.join(path_to_save_location, "%(title)s.%(ext)s")


def is_valid_indexing_file(indexing_file_name: str) -> bool:
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in indexing_file_name: return False
    return True


def import_config() -> tuple[str, str, str | None]:
    import configparser
    config = configparser.ConfigParser()
    try:
        config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", CONF_FILE_NAME))
        if len(config) == 0:
            raise FileNotFoundError("Configuration file does not exist or cannot be opened.")
        if not config.sections():
            raise configparser.MissingSectionHeaderError(
                CONF_FILE_NAME,
                0,
                "Configuration file is empty or missing section headers."
            )
        index_file_name = os.path.normpath(config['indexing']['index_file_name'])
        indexing_format = config['indexing']['indexing_format']
        default_download_location = config['indexing']['default_download_location']
        video_only = config['downloading']['video_only']
        max_size = config['downloading']['max_download_size']
        max_video_quality = config['downloading']['max_video_quality']
        max_audio_quality = config['downloading']['max_audio_quality']
        encoding_standard = config['encoding']['encoding_standard']
        crf = config['encoding']['crf']
        use_h265 = config['encoding']['use_h265']
        if max_video_quality not in allowed_video_formats: raise ValueError(
            f"Invalid max video quality. Must be one of the following: {", ".join(allowed_video_formats)}. Number to quality mapping: {get_video_format_mapping_str()}")
        if max_audio_quality not in allowed_audio_format: raise ValueError(
            f"Invalid max audio quality. Must be one of the following: {", ".join(allowed_audio_format)}. Number to quality mapping: {get_audio_format_mapping_str()}")
        if encoding_standard not in allowed_encoding_standards: raise ValueError(
            f"Invalid encoding standard. Must be one of the following: {", ".join(allowed_encoding_standards)}. Number to standard mapping: {encoding_standard_to_preset}")
        if crf not in allowed_crf_standards: raise ValueError(
            f"Invalid CRF standard. Must be one of the following: {", ".join(allowed_crf_standards)}. Number to standard mapping: {crf_standard_to_value}")
        if video_only != 'true' and video_only != 'false': raise ValueError(
            "video_only must be either 'true' or 'false'.")
        if use_h265 != 'true' and use_h265 != 'false': raise ValueError("use_h265 must be either 'true' or 'false'.")
        if video_only == 'true':
            change_to_video_only_conversion_setup(encoding_standard, crf, use_h265 == 'true')
        else:
            if max_video_quality == '-1':
                change_to_audio_only_conversion_setup(max_audio_quality)
            else:
                add_video_format_setup(max_video_quality)
                change_to_default_conversion_setup(max_audio_quality, encoding_standard, crf, use_h265 == 'true')
        if max_size != '-1': add_max_file_size_setup(max_size)

        if not is_valid_indexing_file(index_file_name):
            raise ValueError("Invalid indexing file name.")
        if default_download_location != "none":
            return index_file_name + ".txt", indexing_format, os.path.normpath(default_download_location)
        return index_file_name + ".txt", indexing_format, None
    except FileNotFoundError:
        sys.exit(Fore.RED + f"Error: Configuration file '{CONF_FILE_NAME}' not found!")
    except configparser.MissingSectionHeaderError as e:
        sys.exit(
            Fore.RED + f"Error: {e}. Ensure the file contains valid section headers: course_saving, authentication.")
    except configparser.ParsingError as e:
        sys.exit(Fore.RED + f"Error: Failed to parse the configuration file. Details: {e}")
    except configparser.NoSectionError as e:
        sys.exit(Fore.RED + f"Error: Missing section in the configuration file. Details: {e}")
    except configparser.NoOptionError as e:
        sys.exit(Fore.RED + f"Error: Missing option in the configuration file. Details: {e}")
    except KeyError as e:
        sys.exit(Fore.RED + f"Error: Missing required key: {e}")
    except ValueError as e:
        sys.exit(Fore.RED + f"Error: {e}")
    except Exception as e:
        sys.exit(Fore.RED + f"An unexpected error occurred: {e}")


def set_up(index_file_path: str, default_save_path: str | None) -> tuple[str, str]:
    if default_save_path is not None:
        print(
            Style.RESET_ALL + f"Detected default save location: {default_save_path}. If you wish to change it, enter the new path below. Otherwise, leave the line empty.")
    user_input = input(Style.RESET_ALL + "Enter the path to the save directory: ")
    if user_input == "" and default_save_path is not None:
        print(Style.RESET_ALL + "Using default save location")
        norm_path = default_save_path
    else:
        norm_path = os.path.normpath(user_input)
    if not os.path.exists(norm_path):
        print(Style.RESET_ALL + "Directory doesn't exist. Creating directory...")
        os.makedirs(norm_path)
    path_to_index_file = os.path.join(norm_path, index_file_path)
    if not os.path.exists(path_to_index_file):
        print(Style.RESET_ALL + "Indexing file doesn't exist. Creating indexing file...")
        with open(path_to_index_file, 'w') as f:
            f.write("")
            f.close()
        print(Style.RESET_ALL + "Indexing file created successfully.")
    else:
        print(Style.RESET_ALL + "Indexing file already exists. Will append to the end of it.")
    add_save_location(norm_path)
    return norm_path, path_to_index_file


def collect_urls() -> list[tuple[str, str]]:
    print(Style.RESET_ALL + "Enter video urls to download one by one. Empty line to finish.\n")
    sanitized_inputs: list[tuple[str, str]] = []
    while True:
        registered_url_count: int = len(sanitized_inputs)
        user_input = input(Style.RESET_ALL +
                           "Copy the whole video url; enter: 'https://www.youtube.com/watch?v=SOME_CODE' (without the quotes): ")
        if not user_input:
            if registered_url_count == 0: sys.exit(Fore.RED + "No URLs registered. Exiting...")
            return sanitized_inputs
        sanitized_url = sanitize_url(user_input)
        if sanitized_url is not None:
            sanitized_inputs.append(sanitized_url)
            print(
                Style.RESET_ALL + f"Registered URL for video: {sanitized_url[1]}. URLs registered: {registered_url_count + 1}.")
        else:
            print(Fore.MAGENTA + "Invalid URL. Skipping...\n")


def sanitize_url(url: str) -> tuple[str, str] | None:
    if len(url) > 32 and url.startswith("https://www.youtube.com/watch?v="):
        next_param = url.find("&", 32)
        if next_param == -1:
            if not validate_video_part(url[32:]): return None
            return url, url[32:]
        else:
            video_part = url[32:next_param]
            if not validate_video_part(video_part): return None
            return url[:next_param], video_part
    else:
        return None


def validate_video_part(video_part: str) -> bool:
    if len(video_part) != 11: return False
    for char in video_part:
        code = ord(char)
        if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122) or code == 45 or code == 95:
            continue
        else:
            return False
    return True


def download_and_index(url_list: list[tuple[str, str]], index_file_path: str, indexing_format: str) -> int:
    current_date = str(date.today())
    success_count: int = 0
    count: int = len(url_list)
    with yt_dlp.YoutubeDL(yt_dlp_options) as downloader:
        with open(index_file_path, 'a') as index_file:
            for url in url_list:
                count -= 1
                try:
                    print(Style.RESET_ALL + f"Attempting to download video: {url[1]}...")
                    info = downloader.extract_info(url[0], download=True)
                    if info is None: raise yt_dlp.DownloadError
                    print(Style.RESET_ALL + f"Downloaded video: {url[1]}")
                    title = info['title']
                    uploader = info['uploader']
                    print(Style.RESET_ALL + f"Indexing video: {title}...")
                    formatted_video_index = indexing_format.replace("[URL]", url[0]).replace("[TITLE]", title).replace(
                        "[PLATFORM]", "YouTube").replace("[DATE]", current_date)
                    formatted_video_index = formatted_video_index.replace("[ARTIST_LIST]", uploader)
                    index_file.write(formatted_video_index + '\n')
                    success_count += 1
                    print(Style.RESET_ALL + f"Indexed video as: {formatted_video_index}")
                    print(Fore.GREEN +
                          f"Downloading and indexing complete. Success count: {success_count} of {len(url_list)}. Videos in queue left: {count}.\n")
                except yt_dlp.DownloadError:
                    print(
                        Fore.RED + f"Failed to download video: {url[1]}. Skipping... Videos in queue left: {count}.\n")
        index_file.close()
        return success_count


def main():
    print(
        Fore.CYAN + "Welcome to YouTube downloader and indexer.\nPlease read README.md file for more information and before using this program.\n")
    print(Style.RESET_ALL + "Importing configuration file...\n")
    index_tuple = import_config()
    print(Fore.GREEN + "Configuration imported successfully.\n")
    index_data = set_up(index_tuple[0], index_tuple[2])
    print(Fore.GREEN + "Setup complete.\n")
    urls = collect_urls()
    print(Fore.GREEN + f"Collecting URLs complete. {len(urls)} collected.\n")
    print(Fore.LIGHTYELLOW_EX + "Starting downloading and indexing...\n")
    download_count = download_and_index(urls, index_data[1], index_tuple[1])
    print(Fore.GREEN + f"Downloading and indexing complete - {download_count} videos.\n" + Style.RESET_ALL)


if __name__ == '__main__':
    main()
