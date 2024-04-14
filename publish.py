#!/usr/bin/env python3

import argparse

from config import Config
from publisher import Build, GithubPublisher, LocalPublisher


def add_config_arg(p):
    p.add_argument('-c', '--config', help='Path to configuration file', nargs='+')


parser = argparse.ArgumentParser(description='Publish builds')

subparsers = parser.add_subparsers(dest='command')
subparsers.required = True

parser_index = subparsers.add_parser('index')
add_config_arg(parser_index)
parser_index.add_argument(
    '-m', '--model', help='Index builds for a given device model')

parser_add = subparsers.add_parser('add')
add_config_arg(parser_add)

parser_add.add_argument('build')

parser_delete = subparsers.add_parser('delete')
add_config_arg(parser_delete)

parser_delete.add_argument('-p', '--dry', help='Only print builds to be deleted', action='store_true')
parser_delete.add_argument('-a', '--all', help='Delete all builds', action='store_true')
parser_delete.add_argument(
    '-m', '--model', help='Delete builds for a given device model')
parser_delete.add_argument(
    '-v', '--version', help='Delete builds for this version')
parser_delete.add_argument(
    '-s', '--start-date', help='Delete builds starting from this date')
parser_delete.add_argument(
    '-e', '--end-date', help='Delete builds ending with this date (inclusive)')
parser_delete.add_argument('-d', '--date', help='Delete builds from this date')

args = parser.parse_args()

for config_path in args.config:
    print(f'Using config {config_path}')

    config = Config(config_path)

    publisher_args = [config.builds_json_path, config.builds_path,
                      config.blacklisted_devices, config.ignored_versions,
                      config.builds_limit]

    if config.github_token:
        publisher = GithubPublisher(
            config.github_token, config.github_organization, *publisher_args)
    else:
        publisher = LocalPublisher(*publisher_args)

    if args.command == 'index':
        if args.model:
            publisher.index_device_builds(args.model)
        else:
            publisher.index_builds()
    elif args.command == 'add':
        try:
            build = Build.from_path(args.build)
            publisher.add_build(build)
        except ValueError as e:
            print(e)
            exit(1)
    elif args.command == 'delete':
        if args.all:
            builds = publisher.find_all_builds()
        else:
            builds = publisher.find_builds(device=args.model, version=args.version,
                                           min_date=args.start_date, max_date=args.end_date,
                                           date=args.date)
        if not builds:
            print(f'No builds found')

        for build in builds:
            if args.dry:
                print(f'Found build {build.name}')
            else:
                print(f'Removing build {build.name}')
                publisher.remove_build(build)
                print(f'Removed build {build.name}')

    print()
