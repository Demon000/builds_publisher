import hashlib
import os
import shutil


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


def remove_filename_ext(filename):
    return os.path.splitext(filename)[0]


def extract_filename_parts(filename):
    name = remove_filename_ext(filename)
    return name.split('-')


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
def is_build(path):
    if not is_file(path):
        return False

    filename = path_filename(path)
    if not filename.endswith('.zip'):
        return False

    parts = extract_filename_parts(filename)

    if len(parts) != 5:
        return False

    if parts[0] != 'lineage':
        return False

    return True
