import os
import re


def extract_filename_parts(filename):
    name = os.path.splitext(filename)
    return name, name.split('-')


def is_device(path, blacklisted_devices):
    if not os.path.isdir(path):
        return False

    device = os.path.basename(path)
    if device in blacklisted_devices:
        return False

    return True


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
def is_build(path):
    if not os.path.isfile(path):
        return False

    filename = os.path.basename(path)
    if not filename.endswith('.zip'):
        return False

    _, parts = extract_filename_parts(filename)

    if len(parts) != 5:
        return False

    if parts[0] != 'lineage':
        return False

    return True
