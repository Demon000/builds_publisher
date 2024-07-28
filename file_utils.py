import hashlib
import os
import shutil
import pathlib


def is_dir(path):
    return os.path.isdir(path)


def is_file(path):
    return os.path.isfile(path)


def is_dir_or_file(path):
    return is_dir(path) or is_file(path)


def delete_dir_or_file(path):
    if is_dir(path):
        shutil.rmtree(path)
    elif is_file(path):
        os.remove(path)
    else:
        raise ValueError(f'{path} is not a file or directory')


def file_size(path):
    return os.path.getsize(path)


def file_sha256(path):
    sha256 = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)

    with open(path, 'rb', buffering=0) as file:
        for index in iter(lambda: file.readinto(mv), 0):
            sha256.update(mv[:index])

    return sha256.hexdigest()


def path_relative(base, path):
    return os.path.relpath(path, base)


def path_filename(path):
    return os.path.basename(path)


def path_join(base_path, path):
    return os.path.join(base_path, path)


def _path_files(path, check_fn, descending):
    if not is_dir(path):
        raise ValueError(f'{path} is not a directory')

    paths = [f for f in os.scandir(path) if check_fn(f.path)]

    paths.sort(key=lambda f: f.name.lower(), reverse=descending)

    paths = [f.path for f in paths]

    return paths


def path_files(path, descending=False):
    return _path_files(path, is_file, descending)


def path_files_or_dirs(path, descending=False):
    return _path_files(path, is_dir_or_file, descending)


def path_dirs(path, descending=False):
    return _path_files(path, is_dir, descending)


valid_extensions = [
    '.img.tar.gz',
    '.img',
    '.zip',
]


def extract_path_name_valid_ext(path):
    filename = path_filename(path)
    for ext in valid_extensions:
        if filename.endswith(ext):
            name = filename[:-len(ext)]
            return name, ext

    return filename, None


def remove_filename_ext_simple(filename):
    return os.path.splitext(filename)[0]


def remove_filename_ext(filename):
    name, ext = extract_path_name_valid_ext(filename)
    if not ext:
        name = remove_filename_ext_simple(filename)
    return name


def extract_name_parts(name):
    return name.split('-')


def extract_filename_parts(filename):
    name, _ = extract_path_name_valid_ext(filename)
    return extract_name_parts(name)


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
# lineage-21.0-20240622-UNOFFICIAL-arm64-gsi.img
def is_build(path):
    if not is_file(path):
        return False

    name, ext = extract_path_name_valid_ext(path)
    if not ext:
        return False

    parts = extract_name_parts(name)
    if len(parts) != 5 and (len(parts) != 6 or parts[5] != 'gsi'):
        return False

    if parts[0] != 'lineage':
        return False

    return True
