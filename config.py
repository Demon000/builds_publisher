import json
import sys


class Config:
    def __init__(self, config_path):
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
        except IOError:
            print("failed to find publisher_config.json file")
            sys.exit(-1)

        self.builds_path = config.get('builds_path')
        self.ignored_versions = config.get('ignored_versions', [])
        self.builds_json_path = config.get('builds_json_path')
        self.builds_limit = config.get('builds_limit', 0)
        self.github_token = config.get('github_token', '')
        self.github_organization = config.get('github_organization', '')
        self.blacklisted_devices = config.get('blacklisted_devices', [])
