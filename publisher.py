#!/usr/bin/python3

import json

from github import Github, GithubException
from datetime import datetime
from time import mktime

from file_utils import *


def raw_date_to_split(raw_date):
    return f'{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}'


def date_to_unix(date, fmt):
    time = datetime.strptime(date, fmt)
    return int(mktime(time.timetuple()))


def raw_date_to_unix(raw_date):
    return date_to_unix(raw_date, '%Y%m%d')


def split_date_to_unix(split_date):
    return date_to_unix(split_date, '%Y-%m-%d')


class BaseFile:
    def __init__(self, path, url, size, sha256, filename):
        self.path = path
        self.url = url
        self.size = size
        self.sha256 = sha256
        self.filename = filename

    def __eq__(self, other):
        return self.filename == other.filename and self.sha256 == other.sha256

    @classmethod
    def deserialize(cls, serialization):
        path = serialization['path']
        url = serialization['filepath']
        size = serialization['size']
        sha256 = serialization['sha256']
        filename = serialization['filename']
        return cls(path, url, size, sha256, filename)

    @classmethod
    def extract_data_from_path(cls, path):
        url = None
        size = file_size(path)
        sha256 = file_sha256(path)
        filename = path_filename(path)
        return path, url, size, sha256, filename

    @classmethod
    def from_path(cls, path):
        args = cls.extract_data_from_path(path)
        return cls(*args)

    def serialize(self):
        serialization = {
            'path': self.path,
            'filename': self.filename,
            'filepath': self.url,
            'sha256': self.sha256,
            'size': self.size,
        }

        return serialization


class RomFile(BaseFile):
    def __init__(self, version, type_, device, os_patch_level, date, date_time, *args):
        super().__init__(*args)

        self.version = version
        self.type = type_
        self.device = device
        self.os_patch_level = os_patch_level
        self.date = date
        self.date_time = date_time

    @classmethod
    def extract_data_from_path(cls, path):
        args = super().extract_data_from_path(path)

        filename = path_filename(path)
        parts = extract_filename_parts(filename)

        version = parts[1]
        raw_date = parts[2]
        type_ = parts[3].lower()
        device = parts[4]
        os_patch_level = None

        date = raw_date_to_split(raw_date)
        date_time = raw_date_to_unix(raw_date)

        return version, type_, device, os_patch_level, date, date_time, *args


class Build:
    def __init__(self, path, device, files, type_, version, date, date_time, os_patch_level):
        self.path = path
        self.device = device
        self.files = files
        self.type = type_
        self.version = version
        self.date = date
        self.date_time = date_time
        self.os_patch_level = os_patch_level

    def __eq__(self, other):
        return self.name == other.name and self.files == other.files

    @property
    def name(self):
        rom_file = self.files[0]
        return remove_filename_ext(rom_file.filename)

    @classmethod
    def deserialize(cls, serialization):
        files = [BaseFile.deserialize(s) for s in serialization['files']]
        path = serialization['path']
        device = serialization['device']
        type_ = serialization['type']
        version = serialization['version']
        date = serialization['date']
        date_time = serialization['datetime']
        os_patch_level = serialization.get('os_patch_level')
        return cls(path, device, files, type_, version, date, date_time, os_patch_level)

    @classmethod
    def from_path(cls, path):
        if is_build(path):
            build_files = [path]
        else:
            build_files = path_files(path)

        if not build_files:
            raise ValueError(f'{path_filename(path)} has no files')

        rom_path = None
        extra_paths = []
        for build_file in build_files:
            if is_build(build_file):
                rom_path = build_file
            else:
                extra_paths.append(build_file)

        if not rom_path:
            raise ValueError(f'{path_filename(path)} has no build')

        rom_file = RomFile.from_path(rom_path)

        files = [rom_file]
        for extra_path in extra_paths:
            extra_file = BaseFile.from_path(extra_path)
            files.append(extra_file)

        device = rom_file.device
        type_ = rom_file.type
        version = rom_file.version
        date = rom_file.date
        date_time = rom_file.date_time
        os_patch_level = rom_file.os_patch_level

        return cls(path, device, files, type_, version, date, date_time, os_patch_level)

    def serialize(self):
        serialization = {
            'path': self.path,
            'device': self.device,
            'type': self.type,
            'version': self.version,
            'date': self.date,
            'datetime': self.date_time,
            'os_patch_level': self.os_patch_level,
            'files': [f.serialize() for f in self.files]
        }

        return serialization


class BuildsJson:
    def __init__(self, path):
        self.__path = path
        self.__devices = None

    def __enter__(self):
        devices = {}

        # Read data from the builds.json file
        try:
            with open(self.__path, 'r') as builds_json_file:
                devices_serialization = json.load(builds_json_file)
        except IOError:
            devices_serialization = {}

        # Deserialize files
        for device, builds_serialization in devices_serialization.items():
            builds = [Build.deserialize(s) for s in builds_serialization]
            devices[device] = builds

        self.__devices = devices

        return devices

    def __exit__(self, exception_type, exception_value, traceback):
        # Serialize files
        devices_serialization = {}
        for device, builds in self.__devices.items():
            builds_serialization = [build.serialize() for build in builds]
            devices_serialization[device] = builds_serialization

        # Write data back into the builds.json file
        with open(self.__path, 'w') as builds_json_file:
            json.dump(devices_serialization, builds_json_file, indent=4)

        return False


class Publisher:
    def __init__(self, builds_json_path, builds_path,
                 blacklisted_devices, ignored_versions, builds_limit):
        self._builds_path = builds_path
        self.__builds_json = BuildsJson(builds_json_path)
        self.__blacklisted_devices = blacklisted_devices
        self.__ignored_versions = ignored_versions
        self.__builds_limit = builds_limit

    def _is_build_uploaded(self, build):
        pass

    def _upload_build(self, build):
        pass

    def _unupload_build(self, build):
        pass

    def _upload_build_file(self, build, file):
        pass

    def _remove_build_file(self, build, file):
        pass

    def _update_build_file(self, build, file):
        pass

    def find_all_builds(self):
        all_builds = []

        with self.__builds_json as devices:
            for builds in devices.values():
                all_builds.extend(builds)

        return all_builds

    def find_builds(self, device=None, version=None, min_date=None, max_date=None, date=None):
        if (min_date is not None or max_date is not None) and date is not None:
            raise ValueError('Cannot filter for both date and min/max date')

        if min_date is None and max_date is None and date is not None:
            min_date = date
            max_date = date

        min_date_unix = None
        if min_date is not None:
            min_date_unix = raw_date_to_unix(min_date)

        max_date_unix = None
        if max_date is not None:
            ONE_DAY_SECONDS = 24 * 60 * 60
            max_date_unix = raw_date_to_unix(max_date) + ONE_DAY_SECONDS

        matching_builds = []

        with self.__builds_json as devices:
            for builds_device_name, builds in devices.items():
                if device is not None and builds_device_name != device:
                    continue

                for build in builds:
                    if version is not None and build.version != version:
                        continue

                    if min_date_unix is not None and \
                            build.date_time < min_date_unix:
                        continue

                    if max_date_unix is not None and \
                            build.date_time >= max_date_unix:
                        continue

                    matching_builds.append(build)

        return matching_builds

    def _get_device_builds(self, devices, device):
        return devices.setdefault(device, [])

    def _get_build_by_name(self, builds, build_name):
        for build in builds:
            if build.name == build_name:
                return build

        return None

    def is_build_skipped(self, build):
        if build.device in self.__blacklisted_devices:
            print(f'Build {build.name} is for blacklisted device {build.device}, skipping')
            return True

        if build.version in self.__ignored_versions:
            print(f'Build {build.name} is for ignored version {build.version}, skipping')
            return True

        return False

    def _unindex_build(self, builds, build):
        try:
            builds.remove(build)
        except ValueError:
            pass

    def _unindex_builds(self, builds, removed_builds):
        for build in removed_builds:
            builds.remove(build)
        return removed_builds

    def _sort_builds_by_datetime(self, builds):
        builds.sort(key=lambda x: x.date_time, reverse=True)

    def _get_more_than_limit_builds(self, builds):
        self._sort_builds_by_datetime(builds)
        if self.__builds_limit == 0:
            return []

        return builds[self.__builds_limit:]

    def _is_device_build_more_than_limit(self, builds, build):
        new_builds = builds[:] + [build]
        old_builds = self._get_more_than_limit_builds(new_builds)
        return build in old_builds

    def _remove_build(self, builds, build):
        self._unupload_build(build)
        self._unindex_build(builds, build)

    def _remove_builds(self, builds, removed_builds):
        for build in removed_builds:
            self._remove_build(builds, build)
        return removed_builds

    def remove_build(self, build):
        with self.__builds_json as devices:
            builds = self._get_device_builds(devices, build.device)
            self._remove_build(builds, build)

    def is_build_uploaded(self, build):
        print(f'Checking if build {build.name} is uploaded')
        return self._is_build_uploaded(build)

    def _unindex_not_uploaded_builds(self, builds):
        unindexed_builds = [b for b in builds if not self.is_build_uploaded(b)]
        return self._unindex_builds(builds, unindexed_builds)

    def _unindex_skipped_builds(self, builds):
        unindexed_builds = [b for b in builds if self.is_build_skipped(b)]
        return self._unindex_builds(builds, unindexed_builds)

    def _remove_more_than_limit_builds(self, builds):
        old_builds = self._get_more_than_limit_builds(builds)
        return self._remove_builds(builds, old_builds)

    def _remove_more_than_limit_builds_print(self, builds):
        removed_builds = self._remove_more_than_limit_builds(builds)
        for build in removed_builds:
            print(f'Build {build.name} exceeds builds limit, removing')
        return removed_builds

    def clean_device_builds(self, devices, device):
        builds = self._get_device_builds(devices, device)

        removed_builds = self._unindex_skipped_builds(builds)
        for build in removed_builds:
            print(f'Build {build.name} is skipped, removing from index')

        removed_builds = self._unindex_not_uploaded_builds(builds)
        for build in removed_builds:
            print(f'Build {build.name} is not uploaded, removing from index')

        self._remove_more_than_limit_builds_print(builds)

    def clean_builds(self, devices):
        for device in devices.keys():
            self.clean_device_builds(devices, device)

        print()

    def _index_device_path(self, devices, device_path):
        device_name = path_filename(device_path)

        print(f'Found device path {device_path}')

        if device_name in self.__blacklisted_devices:
            print(f'Device path {device_path} is for blacklisted device {device_name}, skipping')
            print()
            return

        build_paths = path_files_or_dirs(device_path, descending=True)

        builds = self._get_device_builds(devices, device_name)
        new_builds = []

        for build_path in build_paths:
            try:
                build = Build.from_path(build_path)
                if device_name != build.device:
                    raise ValueError(f'Device path {device_path} contains ' +
                                     f'build {build.name} for device {build.device}')

                new_builds.append(build)
            except ValueError as e:
                print(e)

        self._add_builds(builds, new_builds)

        print()

    def index_device_builds(self, device):
        path = path_join(self._builds_path, device)

        print(f'Indexing path {path}')

        with self.__builds_json as devices:
            self.clean_device_builds(devices, device)

            self._index_device_path(devices, path)

    def index_builds(self):
        print(f'Indexing path {self._builds_path}')

        device_paths = path_dirs(self._builds_path)

        with self.__builds_json as devices:
            self.clean_builds(devices)

            for device_path in device_paths:
                self._index_device_path(devices, device_path)

    def index_build(self, path):
        print(f'Indexing path {path}')

        build = Build.from_path(path)
        self.add_build(build)

    def _update_build(self, existing_build, build):
        # Find all files that are not exactly the same inside the
        # updated build and remove them from the existing build
        removed_files = []
        for existing_file in existing_build.files:
            found = False

            for file in build.files:
                if file == existing_file:
                    found = True
                    break

            if not found:
                removed_files.append(existing_file)

        for file in removed_files:
            print(f'Removing old file {file.filename}')
            self._remove_build_file(existing_build, file)
            existing_build.files.remove(file)

        # Find all files that are not exactly the same inside the
        # existing build and add them to the existing build
        added_files = []
        for file in build.files:
            found = False

            for existing_file in existing_build.files:
                if file == existing_file:
                    found = True
                    break

            if not found:
                added_files.append(file)

        for file in added_files:
            print(f'Uploading new file {file.filename}')
            self._upload_build_file(build, file)
            existing_build.files.append(file)

    def _add_builds(self, builds, new_builds):
        removed_builds = self._remove_more_than_limit_builds_print(builds)

        for build in new_builds:
            # This is not actually a new build, it was just removed earlier
            # because it exceeded the limit after a more recent build has
            # been added. Do not try adding it again.
            if build in removed_builds:
                continue

            self._add_build(builds, build)
            new_removed_builds = self._remove_more_than_limit_builds_print(builds)
            removed_builds = removed_builds + new_removed_builds

    def _add_build(self, builds, build):
        if self.is_build_skipped(build):
            return

        existing_build = self._get_build_by_name(builds, build.name)

        if existing_build is None \
                and self._is_device_build_more_than_limit(builds, build):
            print(f'Found new build {build.name} that exceeds builds limit, removing')
            self._unupload_build(build)
        elif existing_build is None:
            print(f'Found new build {build.name}')
            self._upload_build(build)
            builds.append(build)
        elif existing_build != build:
            print(f'Found existing build {build.name} with changes, updating')
            self._update_build(existing_build, build)
        else:
            print(f'Found existing build {build.name}')

        print()

    def add_build(self, build):
        with self.__builds_json as devices:
            builds = self._get_device_builds(devices, build.device)
            self._add_builds(builds, [build])


class LocalPublisher(Publisher):
    def __init__(self, *args):
        super().__init__(*args)

    def _is_build_uploaded(self, build):
        return is_dir_or_file(build.path)

    def _unupload_build(self, build):
        try:
            delete_dir_or_file(build.path)
        except FileNotFoundError:
            pass

    def _upload_build(self, build):
        for file in build.files:
            file.url = path_relative(self._builds_path, file.path)


class GithubPublisher(Publisher):
    def __init__(self, github_token, github_organization, *args):
        super().__init__(*args)

        self._github = Github(github_token)

        if github_organization:
            self._repo_place = self._github.get_organization(
                github_organization)
        else:
            self._repo_place = self._github.get_user()

    def _create_empty_repo(self, build):
        repo = self._repo_place.create_repo(build.device)
        repo.create_file('README', 'initial commit', build.device)
        return repo

    def _find_repo(self, build):
        try:
            return self._repo_place.get_repo(build.device)
        except GithubException as e:
            print(e)
            return None

    def _get_repo(self, build):
        repo = self._find_repo(build)

        if repo is None:
            repo = self._create_empty_repo(build)

        return repo

    def _get_release(self, repo, build):
        return repo.get_release(build.name)

    def _delete_release(self, repo, build):
        release = self._get_release(repo, build)
        release.delete_release()

    def _create_empty_release(self, repo, build):
        try:
            self._delete_release(repo, build)
        except GithubException:
            pass

        return repo.create_git_release(build.name, build.name, build.name)

    def _unupload_build(self, build):
        repo = self._find_repo(build)
        if repo is None:
            return

        try:
            self._delete_release(repo, build)
        except GithubException:
            pass

    def _is_build_uploaded(self, build):
        repo = self._find_repo(build)
        if repo is None:
            return False

        release = self._get_release(repo, build)
        return release is not None

    def _upload_file(self, release, file):
        try:
            self._remove_file(release, file)
        except GithubException:
            pass

        asset = release.upload_asset(file.path)

        file.url = asset.browser_download_url

    def _upload_build_file(self, build, file):
        repo = self._get_repo(build)
        release = self._get_release(repo, build)

        self._upload_file(release, file)

    def _remove_file(self, release, file):
        try:
            assets = release.assets
        except AttributeError:
            assets = release.get_assets()

        for asset in assets:
            if asset.name == file.filename:
                asset.delete_asset()

    def _remove_build_file(self, build, file):
        repo = self._get_repo(build)
        release = self._get_release(repo, build)
        self._remove_file(release, file)

    def _upload_build(self, build):
        repo = self._get_repo(build)
        release = self._create_empty_release(repo, build)

        for file in build.files:
            print(f'Uploading file {file.filename}')
            self._upload_file(release, file)
            print(f'Uploaded file {file.filename}')
