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


class Build:
    def __init__(self, path=None, recovery_path=None, serialization=None):
        if path is not None:
            self.path = path
            self.url = None
            self.size = os.path.getsize(path)
            self.sha256 = get_sha256(path)
            self.filename = os.path.basename(path)

            if recovery_path is not None:
                self.recovery = Build(path=recovery_path)
            else:
                self.recovery = None
        elif serialization is not None:
            self.path = None
            self.url = serialization['filepath']
            self.size = serialization['size']
            self.sha256 = serialization['sha256']
            self.filename = serialization['filename']

            if 'recovery' in serialization:
                self.recovery = Build(serialization=serialization['recovery'])
            else:
                self.recovery = None

        self.name = os.path.splitext(self.filename)[0]

        _, version, raw_date, type_, device = self.name.split('-')
        self.version = version
        self.type = type_.lower()
        self.device = device

        self.date = '{}-{}-{}'.format(raw_date[0:4], raw_date[4:6], raw_date[6:8])

    def upload(self, github_user):
        # Upload recovery first
        if self.recovery is not None:
            self.recovery.upload(github_user)

        # Build is already uploaded
        if self.url is not None:
            print(f'build {self.filename} already uploaded')
            return

        # Try to create the repo, if it exists, skip the creation
        try:
            repo = github_user.create_repo(self.device)
            repo.create_file('README', 'initial commit', self.device)
        except:
            repo = github_user.get_repo(self.device)

        # Try to create the release, if it exists, destroy it and upload
        # the file again
        try:
            release = repo.get_release(self.name)
            release.delete_release()
        except:
            pass

        release = repo.create_git_release(self.name, self.name, self.name)
        release.upload_asset(self.path)

        print(f'uploaded build {self.filename}')

        github_username = github_user.login
        self.url = 'https://github.com/{}/{}/releases/download/{}/{}' \
            .format(github_username, self.device, self.name, self.filename)

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

        if self.recovery:
            serialization['recovery'] = self.recovery.serialize()

        return serialization


class Publisher:
    def __init__(self, github_token, builds_json_path):
        self.__github_user = Github(github_token).get_user()
        self.__builds_json_path = builds_json_path
        self.__builds = []

        self.read_builds()

    def find_build_with_name(self, name):
        for build in self.__builds:
            if build.name == name:
                return build

        return None

    def add_build_from_path(self, build_path, recovery_path=None):
        new_build = Build(path=build_path, recovery_path=recovery_path)
        existing_build = self.find_build_with_name(new_build.name)

        print(f'adding build {new_build.filename}')

        # If a build with the same name does not already exist
        if existing_build is None:
            # Then add the new build to the list
            # and return it
            self.__builds.append(new_build)
            return new_build
        else:
            print('\tfound existing build')

        # If the existing build does not have a recovery
        # or if the new build has a different recovery,
        # add the new recovery to the existing build
        # Otherwise, add the existing recovery which is
        # already uploaded to the new build
        if existing_build.recovery is None or \
                existing_build.recovery.sha256 != new_build.recovery.sha256:
            print('\texisting recovery is outdated')
            existing_build.recovery = new_build.recovery
        else:
            print('\texisting recovery is the same as new recovery, using existing recovery')
            new_build.recovery = existing_build.recovery

        # If the existing build has the same sha256 as the old build
        # return the existing build
        if existing_build.sha256 == new_build.sha256:
            print('\texisting build is the same as new build, using existing build')
            # and if they have the same sha256,
            # return the old build
            return existing_build

        # Otherwise, remove the existing build from the list,
        # add the new build, and return it
        print('\texisting build is outdated')
        self.__builds.remove(existing_build)
        self.__builds.append(new_build)
        return new_build

    def publish_build(self, build):
        # Upload the build to github
        build.upload(self.__github_user)
        self.save_builds()

    def read_builds(self):
        # Read data from the builds.json file
        with open(self.__builds_json_path, 'r') as builds_json_file:
            devices_data = json.load(builds_json_file)

        # Deserialize builds
        for device, serializations in devices_data.items():
            builds = [Build(serialization=serialization)
                      for serialization in serializations]
            self.__builds.extend(builds)

    def save_builds(self):
        # Group builds by device
        devices = {}
        for build in self.__builds:
            if not build.device in devices:
                devices[build.device] = []

            devices[build.device].append(build)

        # Serialize builds
        devices_data = {}
        for device, builds in devices.items():
            builds.sort(key=lambda build: build.date)
            devices_data[device] = [build.serialize() for build in builds]

        # Write data back into the builds.json file
        with open(self.__builds_json_path, 'w') as builds_json_file:
            json.dump(devices_data, builds_json_file)
