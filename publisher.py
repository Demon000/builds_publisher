#!/usr/bin/python3

import hashlib
import json
import os

from github import Github


def get_sha256(path):
    sha256 = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)

    with open(path, 'rb', buffering=0) as file:
        for index in iter(lambda: file.readinto(mv), 0):
            sha256.update(mv[:index])

    return sha256.hexdigest()


class BaseFile:
    def __init__(self, path=None, serialization=None):
        if path is not None:
            self.path = path
            self.url = None
            self.size = os.path.getsize(path)
            self.sha256 = get_sha256(path)
            self.filename = os.path.basename(path)
        elif serialization is not None:
            self.path = None
            self.url = serialization['filepath']
            self.size = serialization['size']
            self.sha256 = serialization['sha256']
            self.filename = serialization['filename']

        self.name = os.path.splitext(self.filename)[0]

        _, version, raw_date, type_, device = self.name.split('-')
        self.version = version
        self.type = type_.lower()
        self.device = device

        self.date = '{}-{}-{}'.format(raw_date[0:4], raw_date[4:6], raw_date[6:8])

    def serialize(self):
        serialization = {
            'date': self.date,
            'filename': self.filename,
            'filepath': self.url,
            'sha256': self.sha256,
            'size': self.size,
            'type': self.type,
            'version': self.version,
        }

        return serialization


class Build(BaseFile):
    def __init__(self, path=None, recovery_path=None, serialization=None):
        super().__init__(path, serialization)

        if path is not None:
            if recovery_path is not None:
                self.recovery = BaseFile(path=recovery_path)
            else:
                self.recovery = None
        elif serialization is not None:
            if 'recovery' in serialization:
                self.recovery = BaseFile(serialization=serialization['recovery'])
            else:
                self.recovery = None

    def serialize(self):
        serialization = super().serialize()

        if self.recovery:
            serialization['recovery'] = self.recovery.serialize()

        return serialization


class FileFactory:
    @staticmethod
    def from_serialization(serialization):
        if serialization['type'] == 'unofficial':
            file = Build(serialization=serialization)
        else:
            file = BaseFile(serialization=serialization)

        return file


class Publisher:
    def __init__(self, upload_fn, builds_json_path):
        self.__upload_fn = upload_fn
        self.__builds_json_path = builds_json_path
        self.__files = []

        self.read()

    def find_file_with_filename(self, filename):
        for file in self.__files:
            if file.filename == filename:
                return file

        return None

    def upload_file(self, file):
        self.__upload_fn(file)
        self.write()

    def upload_build(self, build):
        self.upload_file(build)

        if build.recovery is not None:
            self.upload_file(build.recovery)

    def __add_file(self, new_file):
        existing_file = self.find_file_with_filename(new_file.filename)

        print(f'adding file {new_file.filename}')

        # If a file with the same name does not already exist
        if existing_file is None:
            # Then add the new file to the list
            # and return it
            self.__files.append(new_file)
            return new_file
        else:
            print('\tfound existing file')

        # If the existing file the same sha256 as the old file
        # return the existing file
        if existing_file.sha256 == new_file.sha256:
            print('\texisting file is the same as new file, using existing file')
            return existing_file

        # Otherwise, remove the existing file from the list,
        # add the new file, and return it
        print('\texisting file is outdated')
        self.__files.remove(existing_file)
        self.__files.append(new_file)
        return new_file

    def add_file_from_path(self, file_path):
        new_file = BaseFile(path=file_path)
        return self.__add_file(new_file)

    def add_build_from_path(self, build_path, recovery_path=None):
        new_build = Build(path=build_path, recovery_path=recovery_path)
        existing_build = self.find_file_with_filename(new_build.filename)

        # If the existing build does not have a recovery
        # or if the new build doesn't have a recovery,
        # or if the new build has a different recovery,
        # set the existing build's recovery to the new one
        # Otherwise, set the new build's recovery to the
        # old one, which is already uploaded
        # This provides parity recovery-wise, so that
        # no matter which of the 2 builds will be kept
        # both will have the same recovery
        if existing_build is not None:
            if existing_build.recovery is None or new_build.recovery is None or \
                    existing_build.recovery.sha256 != new_build.recovery.sha256:
                print('\trecovery has been added, changed, or removed, using new recovery')
                existing_build.recovery = new_build.recovery
            else:
                print('\texisting recovery is the same as new recovery, using existing recovery')
                new_build.recovery = existing_build.recovery

        return self.__add_file(new_build)

    def read(self):
        # Read data from the builds.json file
        with open(self.__builds_json_path, 'r') as builds_json_file:
            devices_data = json.load(builds_json_file)

        # Deserialize files
        for device, serializations in devices_data.items():
            files = [FileFactory.from_serialization(serialization)
                     for serialization in serializations]
            self.__files.extend(files)

    def write(self):
        # Group files by device
        devices = {}
        for file in self.__files:
            if file.device not in devices:
                devices[file.device] = []

            devices[file.device].append(file)

        # Serialize files
        devices_data = {}
        for device, files in devices.items():
            files.sort(key=lambda b: b.date)
            devices_data[device] = [file.serialize() for file in files]

        # Write data back into the builds.json file
        with open(self.__builds_json_path, 'w') as builds_json_file:
            json.dump(devices_data, builds_json_file)

    @staticmethod
    def create_github_publisher(github_token, builds_json_path):
        github_user = Github(github_token).get_user()

        def upload_file_fn(file):
            # File is already uploaded
            if file.url is not None:
                print(f'file {file.filename} already uploaded')
                return

            # Try to create the repo, if it exists, skip the creation
            try:
                repo = github_user.create_repo(file.device)
                repo.create_file('README', 'initial commit', file.device)
            except:
                repo = github_user.get_repo(file.device)

            # Try to delete the release if it exists
            try:
                release = repo.get_release(file.name)
                release.delete_release()
            except:
                pass

            # Create the release
            release = repo.create_git_release(file.name, file.name, file.name)
            release.upload_asset(file.path)

            print(f'uploaded file {file.filename}')

            github_username = github_user.login
            file.url = 'https://github.com/{}/{}/releases/download/{}/{}' \
                .format(github_username, file.device, file.name, file.filename)

        return Publisher(upload_file_fn, builds_json_path)
