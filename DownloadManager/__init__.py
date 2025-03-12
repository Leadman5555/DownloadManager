import os
import sys

from DownloadManager.message_handler import MessageHandler

CONF_FILE_NAME = "download_manager.ini"
allowed_video_formats = ['6', '5', '4', '3', '2', '1', '0', '-1']
video_format_to_quality: dict[str, str | None] = {
    '-1': None,
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
PATH_TO_INDEX_FILE = 'path_to_index_file'
INDEX_FILE_NAME = 'index_file_name'
INDEXING_FORMAT = 'indexing_format'
PATH_TO_DOWNLOAD_LOCATION = 'default_download_location'
VIDEO_ONLY = 'video_only'
MAX_DOWNLOAD_SIZE = 'max_download_size'
MAX_VIDEO_QUALITY = 'max_video_quality'
MAX_AUDIO_QUALITY = 'max_audio_quality'
ENCODING_STANDARD = 'encoding_standard'
CRF = 'crf'
USE_H265 = 'use_h265'

config_keys = [
    INDEX_FILE_NAME,
    PATH_TO_INDEX_FILE,
    INDEXING_FORMAT,
    PATH_TO_DOWNLOAD_LOCATION,
    VIDEO_ONLY,
    MAX_DOWNLOAD_SIZE,
    MAX_VIDEO_QUALITY,
    MAX_AUDIO_QUALITY,
    ENCODING_STANDARD,
    CRF,
    USE_H265,
]


def is_valid_indexing_file(indexing_file_name: str) -> bool:
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in indexing_file_name: return False
    return True


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


def import_config() -> dict[str, str | bool | None]:
    downloader_config: dict[str, str | bool | None] = dict.fromkeys(config_keys, None)
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
        if not is_valid_indexing_file(index_file_name):
            raise ValueError("Invalid indexing file name.")
        if default_download_location != "none":
            downloader_config[PATH_TO_DOWNLOAD_LOCATION] = os.path.normpath(default_download_location)
        downloader_config[INDEX_FILE_NAME] = f'{index_file_name}.txt'
        downloader_config[INDEXING_FORMAT] = indexing_format
        downloader_config[VIDEO_ONLY] = True if video_only == 'true' else False
        if max_size != '-1':
            downloader_config[MAX_DOWNLOAD_SIZE] = max_size
        downloader_config[MAX_VIDEO_QUALITY] = video_format_to_quality[max_video_quality]
        downloader_config[MAX_AUDIO_QUALITY] = audio_format_to_quality[max_audio_quality]
        downloader_config[ENCODING_STANDARD] = encoding_standard_to_preset[encoding_standard]
        downloader_config[CRF] = crf_standard_to_value[crf]
        downloader_config[USE_H265] = True if use_h265 == 'true' else False
        return downloader_config
    except FileNotFoundError:
        MessageHandler.error(f"Error: Configuration file '{CONF_FILE_NAME}' not found!")
        sys.exit(1)
    except configparser.MissingSectionHeaderError as e:
        MessageHandler.error(
            f"Error: {e}. Ensure the file contains valid section headers: course_saving, authentication.")
        sys.exit(1)
    except configparser.ParsingError as e:
        MessageHandler.error(f"Error: Failed to parse the configuration file. Details: {e}")
        sys.exit(1)
    except configparser.NoSectionError as e:
        MessageHandler.error(f"Error: Missing section in the configuration file. Details: {e}")
        sys.exit(1)
    except configparser.NoOptionError as e:
        MessageHandler.error(f"Error: Missing option in the configuration file. Details: {e}")
        sys.exit(1)
    except KeyError as e:
        MessageHandler.error(f"Error: Missing required key: {e}")
        sys.exit(1)
    except ValueError as e:
        MessageHandler.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        MessageHandler.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
