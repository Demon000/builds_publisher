#!/usr/bin/python3
import json
import os
import sys
import shutil

from file_utils import is_device, is_build
from publisher import LocalPublisher, GithubPublisher


if len(sys.argv) < 2:
    print(f'usage python {sys.argv[0]} /path/to/config.json')
    sys.exit(-1)

config_path = sys.argv[1]

try:
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
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
ignored_versions = get_config('ignored_versions', [])
builds_json_path = get_config('builds_json_path')
builds_limit = get_config('builds_limit', 0)
github_token = get_config('github_token', '')
blacklisted_devices = get_config('blacklisted_devices', [])

old_build_paths = []
new_build_paths = []

def try_int(s):
    try:
        return int(s)
    except:
        return s

devices = [file.path for file in os.scandir(builds_path) if is_device(file.path, blacklisted_devices)]
for device in devices:
    device_build_paths = [file.path for file in os.scandir(device) if os.path.isdir(file.path)]
    device_build_paths.sort(key=lambda x: try_int(x))

    if not device_build_paths:
        continue

    print(f'found device {device}')

    for build_path in device_build_paths:
        print(f'found build {os.path.basename(build_path)}')

    old_build_paths.extend(device_build_paths[:-builds_limit])
    new_build_paths.extend(device_build_paths[-builds_limit:])

for build_path in old_build_paths:
    print(f'removing old build {os.path.basename(build_path)} from disk')
    shutil.rmtree(build_path)

if github_token == '':
    print('creating local publisher')
    publisher = LocalPublisher(builds_path, builds_json_path, ignored_versions)
else:
    print('creating github publisher')
    publisher = GithubPublisher(github_token, builds_json_path, ignored_versions)

for build_path in new_build_paths:
    build_files = [file.path for file in os.scandir(build_path)]

    if not build_files:
        print(f'found build {os.path.basename(build_path)} without files')
        continue

    rom_path = None
    extra_paths = []
    for build_file in build_files:
        if is_build(build_file):
            rom_path = build_file
        else:
            extra_paths.append(build_file)

    if not rom_path:
        print(f'found build {build_path} without zip')
        continue

    publisher.add_build_from_path(rom_path, extra_paths)

print('completed')
