#!/usr/bin/env python3
import os
import sys

from DownloadManager.message_handler import MessageHandler
from DownloadManager.downloaders.downloaders import create_downloaders, BaseDownloader, match_url_to_platform, Indexer
from DownloadManager import PATH_TO_DOWNLOAD_LOCATION, PATH_TO_INDEX_FILE, INDEX_FILE_NAME, INDEXING_FORMAT


def task_finished_hook(d):
    if d['status'] == 'finished':
        MessageHandler.success('Done downloading a stream, now downloading the next one or converting and compressing, may take a while...\n')


def set_up(downloader_config: dict[str, str | bool | None]):
    default_save_path = downloader_config[PATH_TO_DOWNLOAD_LOCATION]
    if default_save_path is not None:
        MessageHandler.info(
            f"Detected default save location: {default_save_path}. If you wish to change it, enter the new path below. Otherwise, leave the line empty.")
    user_input = MessageHandler.receive_input("Enter the path to the save directory: ")
    if user_input == "" and default_save_path is not None:
        MessageHandler.info("Using default save location")
        norm_path = default_save_path
    else:
        norm_path = os.path.normpath(user_input)
    if not os.path.exists(norm_path):
        MessageHandler.info("Directory doesn't exist. Creating directory...")
        try:
            os.makedirs(norm_path)
            downloader_config[PATH_TO_DOWNLOAD_LOCATION] = norm_path
            MessageHandler.info("Directory created successfully.")
        except PermissionError:
            MessageHandler.error("Permission denied: Cannot create directory for file saving.")
            sys.exit(1)
        except OSError as e:
            MessageHandler.error(
                f"OS-related error occurred. Cannot create directory for file saving. Details: {e}")
            sys.exit(1)
    else:
        MessageHandler.info("Directory already exists. Will use it for file saving.")
    path_to_index_file = os.path.join(norm_path, downloader_config[INDEX_FILE_NAME])
    if not os.path.exists(path_to_index_file):
        MessageHandler.info("Indexing file doesn't exist. Creating indexing file...")
        try:
            with open(path_to_index_file, 'w') as f:
                f.write("")
                f.close()
            downloader_config[PATH_TO_INDEX_FILE] = path_to_index_file
            MessageHandler.info("Indexing file created successfully.")
        except PermissionError:
            MessageHandler.error("Permission denied: Indexing will not be performed.")
        except OSError as e:
            MessageHandler.error(f"OS-related error occurred. Indexing will not be performed. Details: {e}")
    else:
        downloader_config[PATH_TO_INDEX_FILE] = path_to_index_file
        MessageHandler.info("Indexing file already exists. Will append to the end of it.")


def collect_urls(downloaders: dict[str, BaseDownloader]) -> tuple[dict[str, list[tuple[str, str, bool]]], int]:
    MessageHandler.info("Registered platforms and their respective URL schemes (links without the quotes):\n")
    for downloader in downloaders.values():
        MessageHandler.info(f"Platform {downloader.platform} -> URL schemes: '{'; '.join(downloader.get_sample_urls())}'")
    MessageHandler.info(f"Total platforms registered {len(downloaders)}\n")
    MessageHandler.info("Enter video or playlist urls to download one by one. Empty line to finish.")
    downloader_to_urls: dict[str, list[tuple[str, str, bool]]] = {}
    registered_url_count: int = 0
    while True:
        user_input = MessageHandler.receive_input(
            "Copy the whole video or playlist url; enter an URL that fits the scheme for platform of your choice (without the quotes): ")
        if not user_input:
            if registered_url_count == 0:
                MessageHandler.info("No URLs registered. Exiting...")
                sys.exit(1)
            return downloader_to_urls, registered_url_count
        match_result: str | None = match_url_to_platform(user_input)
        if match_result is not None:
            downloader = downloaders.get(match_result, None)
            if downloader is None:
                MessageHandler.error("No downloader registered for the chosen platform. Skipping...")
            else:
                sanitation_result: tuple[str, str, bool] | None = downloader.sanitize_url(user_input)
                if sanitation_result is None:
                    MessageHandler.error(
                        f"Malformed URL - matches {match_result} but does not meet requirements. Skipping...")
                else:
                    downloader_to_urls.setdefault(match_result, []).append(sanitation_result)
                    registered_url_count += 1
                    if sanitation_result[2]:
                        MessageHandler.info(f"Registered URL for {match_result} and for playlist {sanitation_result[1]}. URLs registered: {registered_url_count}.")
                        MessageHandler.info("Playlist has been registered. If you wish to download just the chosen video, please paste the URL of the video instead of the playlist.")
                        if MessageHandler.receive_input("Type 'cancel' to remove the playlist url. Empty line or any other input to confirm.").lower() == "cancel":
                            downloader_to_urls[match_result].pop()
                            MessageHandler.info("Playlist url removed.")
                            registered_url_count -= 1
                    else:
                        MessageHandler.info(f"Registered URL for {match_result} and for video: {sanitation_result[1]}. URLs registered: {registered_url_count}.")
        else:
            MessageHandler.error("Invalid URL - does not match any registered domain. Skipping...")


def main():
    from DownloadManager import import_config, MAX_DOWNLOAD_SIZE, MAX_AUDIO_QUALITY, MAX_VIDEO_QUALITY, USE_H265, \
        ENCODING_STANDARD, CRF, VIDEO_ONLY
    MessageHandler.banner("Welcome to Download Manager.")
    MessageHandler.banner("Please read README.md file for more information and before using this program.")
    MessageHandler.info("Importing configuration file...\n")
    downloader_config = import_config()
    MessageHandler.success("Configuration imported successfully.\n")
    set_up(downloader_config)
    MessageHandler.success("Setup complete.\n")
    MessageHandler.info("Creating downloader instances...\n")
    downloaders: dict[str, BaseDownloader] = create_downloaders(
        False,
        MessageHandler,
        task_finished_hook,
        downloader_config[VIDEO_ONLY],
        downloader_config[CRF],
        downloader_config[ENCODING_STANDARD],
        downloader_config[USE_H265],
        downloader_config[MAX_VIDEO_QUALITY],
        downloader_config[MAX_AUDIO_QUALITY],
        downloader_config[MAX_DOWNLOAD_SIZE],
        downloader_config[PATH_TO_DOWNLOAD_LOCATION]
    )
    downloader_to_urls, url_count = collect_urls(downloaders)
    MessageHandler.success(f"Collecting URLs complete. {url_count} collected.\n")
    MessageHandler.info("Starting downloading and indexing...\n")
    indexer: Indexer = Indexer(downloader_config[PATH_TO_INDEX_FILE], downloader_config[INDEXING_FORMAT])
    total_download_success = 0
    total_index_success = 0
    for key in downloader_to_urls:
        current_downloader = downloaders[key]
        MessageHandler.info(f"Downloading and indexing entries for platform {current_downloader.platform}...\n")
        download_success_count, index_success_count = current_downloader.download_and_index(downloader_to_urls[key],indexer)
        total_download_success += download_success_count
        total_index_success += index_success_count
        MessageHandler.success(
            f"Downloading and indexing for {current_downloader.platform} complete - downloaded {download_success_count} and indexed {index_success_count} entries out of {len(downloader_to_urls[key])}.\n")
    MessageHandler.success(
        f"Downloading finished for all platforms. Downloaded {total_download_success} and indexed {total_index_success} entries out of {url_count}")


if __name__ == '__main__':
    main()
