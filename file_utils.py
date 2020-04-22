import os
import re


def extract_filename_parts(filename):
    name = os.path.splitext(filename)[0]
    return name.split('-')


def extract_parts_from_path(file_path):
    filename = os.path.basename(file_path)
    return extract_filename_parts(filename)


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
def extract_date_from_path(file_path):
    filename = os.path.basename(file_path)
    parts = extract_filename_parts(filename)
    return parts[2]


def is_device(file, blacklisted_devices):
    if not file.is_dir():
        return False

    device = os.path.basename(file.path)
    if device in blacklisted_devices:
        return False

    return True


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
def is_build(file):
    if not file.is_file():
        return False

    filename = os.path.basename(file.path)
    if not filename.endswith('.zip'):
        return False

    parts = extract_filename_parts(filename)

    if len(parts) != 5:
        return False

    if parts[0] != 'lineage':
        return False

    if parts[3] != 'UNOFFICIAL':
        return False

    return True


# lineage-17.1-20200422-recovery-bardock.img
def is_recovery(file):
    if not file.is_file():
        return False

    filename = os.path.basename(file.path)
    if not filename.endswith('.img'):
        return False

    parts = extract_filename_parts(filename)

    if len(parts) != 5:
        return False

    if parts[0] != 'lineage':
        return False

    if parts[3] != 'recovery':
        return False

    return True


def is_other_regex(file, whitelisted_files_regex):
    if not file.is_file():
        return False

    filename = os.path.basename(file.path)
    for pattern in whitelisted_files_regex:
        match = re.match(pattern, filename)
        if match:
            return True

    return False


# lineage-17.1-20200422-UNOFFICIAL-bardock.zip
# lineage-17.1-20200422-recovery-bardock.img
def is_recovery_path_matching_build_path_device(recovery_path, build_path):
    recovery_parts = extract_parts_from_path(recovery_path)
    build_parts = extract_parts_from_path(build_path)

    if recovery_parts[4] != build_parts[4]:
        return False

    return True


def find_recovery_path_for_build_path(build_path, recovery_paths):
    device_recovery_paths = []
    for recovery_path in recovery_paths:
        if is_recovery_path_matching_build_path_device(recovery_path, build_path):
            device_recovery_paths.append(recovery_path)

    device_recovery_paths.sort()
    device_build_date = extract_date_from_path(build_path)
    final_recovery_path = None
    for recovery_path in device_recovery_paths:
        recovery_build_date = extract_date_from_path(recovery_path)

        # The recovery build date is older or equal to the device build date,
        # we have found the best recovery for now
        if recovery_build_date <= device_build_date:
            final_recovery_path = recovery_path
            continue

        # We haven't found our recovery until now, which means that
        # there is no recovery older or equal to the device build date
        # take the first recovery you see, it will surely be newer than the
        # device build date
        if final_recovery_path is None:
            final_recovery_path = recovery_path

        # We surely have a recovery now, exit the loop
        break

    build_name = os.path.basename(build_path)
    if final_recovery_path is None:
        print(f"failed to find recovery for build {build_name}")
    else:
        recovery_name = os.path.basename(final_recovery_path)
        print(f"found recovery {recovery_name} for build {build_name}")

    return final_recovery_path
