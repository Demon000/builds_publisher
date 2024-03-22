#!/usr/bin/python3

import hashlib
import json
import os
from os.path import relpath

from github import Github
from datetime import datetime
from time import mktime

from file_utils import extract_filename_parts


def get_sha256(path):
    sha256 = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)

    with open(path, 'rb', buffering=0) as file:
        for index in iter(lambda: file.readinto(mv), 0):
            sha256.update(mv[:index])

    return sha256.hexdigest()


def split_raw_date(raw_date):
    return '{}-{}-{}'.format(raw_date[0:4], raw_date[4:6], raw_date[6:8])


def unix_raw_rate(raw_date):
    time = datetime.strptime(raw_date, '%Y%m%d')
    return int(mktime(time.timetuple()))

class BaseFile:
    def __init__(self, path=None, serialization=None):
        if path is not None:
            self.path = path
            self.url = None
            self.size = os.path.getsize(path)
            self.sha256 = get_sha256(self.path)
            self.filename = os.path.basename(path)
        elif serialization is not None:
            self.path = None
            self.url = serialization['filepath']
            self.size = serialization['size']
            self.sha256 = serialization['sha256']
            self.filename = serialization['filename']

    def __eq__(self, other):
        return self.sha256 == other.sha256

    def serialize(self):
        serialization = {
            'filename': self.filename,
            'filepath': self.url,
            'sha256': self.sha256,
            'size': self.size,
        }

        return serialization

class RomFile(BaseFile):
    def __init__(self, path):
        super().__init__(path)

        name, parts = extract_filename_parts(self.filename)

        self.name = name
        self.version = parts[1]
        raw_date = parts[2]
        self.type = parts[3].lower()
        self.device = parts[4]

        self.date = split_raw_date(raw_date)
        self.datetime = unix_raw_rate(raw_date)

class Build:
    def __init__(self, files=None, serialization=None):
        if files is not None:
            rom_file = files[0]
            self.files = files
            self.type = rom_file.type
            self.version = rom_file.version
            self.date = rom_file.date
            self.datetime = rom_file.datetime
        elif serialization is not None:
            self.files = [BaseFile(serialization=file_serialization) for file_serialization in serialization['files']]
            self.type = serialization['type']
            self.version = serialization['version']
            self.date = serialization['date']
            self.datetime = serialization['datetime']

    def __eq__(self, other):
        return self.files == other.files

    def serialize(self):
        serialization = {
            'type': self.type,
            'version': self.version,
            'date': self.date,
            'datetime': self.datetime,
            'files': [file.serialize() for file in self.files]
        }

        return serialization


class Publisher:
    def __init__(self, builds_json_path, ignored_versions):
        self.__builds_json_path = builds_json_path
        self.__ignored_versions = ignored_versions
        self.__devices = {}

        self._read()

    def add_build_from_path(self, rom_path, extra_paths):
        rom_file = RomFile(rom_path)

        print(f'found {rom_file.filename}')

        if rom_file.version in self.__ignored_versions:
            print(f'{rom_file.filename} is in ignored version, skipping')
            return

        files = [rom_file]
        for extra_path in extra_paths:
            extra_file = BaseFile(extra_path)
            print(f'found {extra_file.filename}')
            files.append(extra_file)

        build = Build(files=files)
        device = rom_file.device

        if device not in self.__devices:
            self.__devices[device] = []

        builds = self.__devices[device]

        if build in builds:
            print(f'{rom_file.filename} exactly matches as existing build, skipping')
            return

        existing_build = None
        for old_build in builds:
            if build.date == old_build.date:
                print(f'{rom_file.filename} overwrites an existing build')
                existing_build = old_build

        self._upload_build(build)

        if existing_build is not None:
            builds.remove(existing_build)

        builds.append(build)

        self._write()

    def _upload_build(self, build):
        pass

    def _read(self):
        # Read data from the builds.json file
        try:
            with open(self.__builds_json_path, 'r') as builds_json_file:
                devices_serialization = json.load(builds_json_file)
        except IOError:
            devices_serialization = {}

        # Deserialize files
        for device, builds_serialization in devices_serialization.items():
            builds = [Build(serialization=build_serialization) for build_serialization in builds_serialization]
            self.__devices[device] = builds

    def _write(self):
        # Serialize files
        devices_serialization = {}
        for device, builds in self.__devices.items():
            builds_serialization = [build.serialize() for build in builds]
            devices_serialization[device] = builds_serialization

        # Write data back into the builds.json file
        with open(self.__builds_json_path, 'w') as builds_json_file:
            json.dump(devices_serialization, builds_json_file, indent=4)

class LocalPublisher(Publisher):
    def __init__(self, base_path, builds_json_path, ignored_versions):
        super().__init__(builds_json_path, ignored_versions)

        self.base_path = base_path

    def _upload_build(self, build):
        for file in build.files:
            file.url = relpath(file.path, self.base_path)

class GithubPublisher(Publisher):
    def __init__(self, github_token, builds_json_path, ignored_versions):
        super().__init__(builds_json_path, ignored_versions)

        self.github_user = Github(github_token).get_user()

    def _get_repo(self, build):
        file = build.files[0]

        # Try to create the repo, if it exists, skip the creation
        try:
            repo = self.github_user.create_repo(build.device)
            repo.create_file('README', 'initial commit', file.device)
        except:
            repo = self.github_user.get_repo(file.device)

        return repo

    def _create_release(self, repo, build):
        file = build.files[0]

        # Try to delete the release if it exists
        try:
            release = repo.get_release(file.name)
            release.delete_release()
        except:
            pass

        # Create the release
        release = repo.create_git_release(file.name, file.name, file.name)

        return release

    def _upload_file(self, repo, release, file):
        print(f'uploading file {file.filename}')

        release.upload_asset(file.path)

        print(f'uploaded file {file.filename}')

        github_username = self.github_user.login
        file.url = 'https://github.com/{}/{}/releases/download/{}/{}' \
            .format(github_username, repo.name, release.tag_name, file.filename)

    def _upload_build(self, build):
        repo = self._get_repo(build)
        release = self._create_release(repo, build)

        file = build.files[0]

        print(f'uploading build {file.filename}')

        for file in build.files:
            self._upload_file(repo, release, file)
