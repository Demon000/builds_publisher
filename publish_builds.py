#!/usr/bin/python3
import json
import os
import sys

from file_utils import is_device, is_build, is_other_regex, is_recovery, find_recovery_path_for_build_path
from publisher import Publisher

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

try:
    with open(os.path.join(__location__, 'publisher_config.json'), 'r') as json_data_file:
        config = json.load(json_data_file)
except IOError:
    print("failed to find publisher_config.json file")
    sys.exit(-1)


def get_config(name, default=None):
    if name not in config:
        if default is not None:
            return default
        else:
            print(f'failed to find {name} in config')
            sys.exit(-1)
    else:
        return config[name]


builds_path = get_config('builds_path')
builds_json_path = get_config('builds_json_path')
builds_limit = get_config('builds_limit', 0)
github_token = get_config('github_token')
blacklisted_devices = get_config('blacklisted_devices', [])
whitelisted_files_regex = get_config('whitelisted_files_regex', [])

old_build_paths = []
new_build_paths = []
other_file_paths = []
recovery_paths = []
devices = [file.path for file in os.scandir(builds_path) if is_device(file, blacklisted_devices)]
for device in devices:
    device_build_paths = [file.path for file in os.scandir(device) if is_build(file)]
    device_build_paths.sort()

    old_build_paths.extend(device_build_paths[:-builds_limit])
    new_build_paths.extend(device_build_paths[-builds_limit:])

    _recovery_paths = [file.path for file in os.scandir(device) if is_recovery(file)]
    recovery_paths.extend(_recovery_paths)

    _other_file_paths = [file.path for file in os.scandir(device) if is_other_regex(file, whitelisted_files_regex)]
    other_file_paths.extend(_other_file_paths)

for build_path in old_build_paths:
    build_name = os.path.basename(build_path)
    print(f'removing old build {build_name} from disk')
    os.remove(build_path)

publisher = Publisher(github_token, builds_json_path)

for build_path in new_build_paths:
    recovery_path = find_recovery_path_for_build_path(build_path, recovery_paths)
    build = publisher.add_build_from_path(build_path, recovery_path)
    publisher.publish_build(build)

for other_path in other_file_paths:
    other = publisher.add_build_from_path(other_path)
    publisher.publish_build(other)

print('completed')
