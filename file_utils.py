import os
import io
import re
import json

"""
Configuration vars
"""

# Buffer size constraints for processing files
MIN_BUFF_SIZE = 4 * 1024
MAX_BUFF_SIZE = 512 * 1024



"""
Directory management
"""

valid_dir_cache = {}

def verify_dir_name(dir: str) -> str:
    """
    Verifies that a directory name is valid before returning a "cleaned"
    version of the directory name.

    If the string provided starts with "./" or ".\\\\", then those starting
    characters are ignored. All leading or trailing slashes are also removed.
    Then, the processed string is checked to see if it obeys safe filename
    rules.

    If it obeys filename rules, the processed string is returned with a forward
    slash appended to the end. Otherwise, a ValueError is raised.
    """
    # Lazy lookup for any directory names already verified.
    if dir in valid_dir_cache:
        return valid_dir_cache[dir]

    __dir = dir
    if dir.startswith("./") or dir.startswith(".\\"):
        __dir = dir[2:]
    __dir = __dir.strip("/\\")

    if not re.search("^\.?[a-zA-Z0-9\-_()\[\] ]{3,}$", __dir):
        raise ValueError("Provided string is not a directory name: " + dir)

    __dir = __dir + "/"
    valid_dir_cache[dir] = __dir
    return __dir

def create_folder(dir: str) -> str:
    """
    Helper method to create a folder, if it doesn't exist.

    Parameters
    ----------
    name: str
        The name of the folder.

    Returns
    -------
    str
        The name of the folder with an additional "./" at the beginning if the
        filepath does not start with one already. This does not return an
        absolute filepath!
    """
    if not os.path.exists(dir):
        os.mkdir("./" + dir)
    return dir

def assemble_dir(*dirs: str, create: bool = True) -> str:
    """
    Tries to assemble a filepath based on the folder specified.

    Parameters
    ----------
    dirs: str
        Directory names.

    create: bool (optional)
        Whether to create each directory as

    Returns
    -------
    str
        A filepath. If only one folder is specified, then the return value is
        "./FOLDER_NAME/". If more than one folder is specified, then each
        folder is treated as a subfolder of the preceeding folder. For example,
        assemble_dir("1", "2") returns "./1/2/".
    """
    final = ""
    for d in dirs:
        final += verify_dir_name(d)
        if create:
            create_folder(final)
    return "./" + final



"""
File reading
"""

def import_json(fpath: str) -> (dict | None):
    """
    Imports the contents of the given JSON file as a dict.

    Parameters
    ----------
    fpath: str
        The filepath of the file to import

    Returns
    -------
    dict | None
        A dict representing the contents of the JSON file, or None if the
        following errors are raised: TimeoutError, PermissionError,
        FileNotFoundError, IsADirectoryError
    """
    res = None
    try:
        with open(fpath, "r") as f:
            res = json.load(f)
    except (TimeoutError, PermissionError, FileNotFoundError, IsADirectoryError):
        pass
    return res

# Credits to:
# https://stackoverflow.com/a/23646049
# https://stackoverflow.com/a/49685142
# https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail#comment92198789_136368
def readline_reverse(fpath: str, sep: bytes = b"\n", encoding: str = "utf-8", buff_size: int = None):
    """
    Reads a file part by part, in reverse. Only returns non-whitespace values.

    Parameters
    ----------
    fpath: str
        The filepath of the file to read

    sep: bytes (optional)
        The string to use to split each part. Defaults to \\n.

    buff_size: int (optional)
        The buffer size to use when reading the file. Defaults to the file's
        block size, or Python's internal limit of 8192 bytes.
    """
    with open(fpath, "rb") as f:
        if not isinstance(buff_size, int):
            buff_size = getattr(os.fstat(f.fileno()), 'st_blksize', io.DEFAULT_BUFFER_SIZE)
        buff_size = min(max(MIN_BUFF_SIZE, buff_size), MAX_BUFF_SIZE)
        leftover = None
        offset = 0
        f.seek(0, os.SEEK_END)
        f_size = r_size = f.tell()

        while r_size > 0:
            offset = min(f_size, offset + buff_size)
            f.seek(f_size - offset)
            buffer = f.read(min(r_size, buff_size))
            r_size -= buff_size
            lines = buffer.split(sep)

            if leftover:
                lines[-1] += leftover
            leftover = lines[0]
            for l in lines[-1:0:-1]:
                l = _decode_and_strip(l, encoding)
                if l:
                    yield l

    leftover = _decode_and_strip(leftover, encoding)
    if leftover:
        yield leftover

def _decode_and_strip(val: bytes, encoding):
    if not isinstance(val, bytes):
        return None
    return val.decode(encoding).strip()
