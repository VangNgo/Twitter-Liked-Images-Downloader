import os
import shutil

import file_utils as futils
import misc_utils as mutils
import persistent_data as pd

"""
Main
"""

def save_temp(id: str, twts: list[str]):
    if id == None:
        raise ValueError("User ID required!")
    if not mutils.isiterable(twts):
        raise ValueError("Not an iterable.")

    fnum = pd.get_data(id, "temp_db.file_num", default=1)
    fname = "%s%s.txt"%(futils.assemble_dir(id, "known_tweets", "temp", create=True), fnum)
    with open(fname, "w") as f:
        for t in twts:
            f.write(str(t) + "\n")
    pd.set_data(id, "temp_db.file_num", set_func=(lambda x: 2 if x == None else x + 1))

def save_to_file(id: str, twts: list[str], limit: int = 5000):
    """
    Adds the provided list of tweets to the set of files detailing tweets
    already processed by this program. These are saved on a per-user basis!

    This method DOES NOT sort the list of tweets for you. It simply processes
    the list of IDs as-is.

    Parameters
    ----------
    id: str
        The ID of the Twitter user.

    twts: list[str]
        The list of tweet IDs to register as "processed."

    limit: int (optional)
        The number of tweet IDs allowed to be saved in a single file. Will be
        automatically corrected to be at least 1000 and at most 10000. Defaults
        to 5000.
    """
    if id == None:
        raise ValueError("User ID required!")
    if not mutils.isiterable(twts):
        raise ValueError("Not an iterable.")
    if not isinstance(limit, int):
        limit = 5000
    limit = min(max(limit, 1000), 10000)

    _save_explicit(id, twts, limit)
    _combine_saves_with_temp(id, limit)

    tmp_dirname = futils.assemble_dir(id, "known_tweets", "temp")
    if os.path.exists(tmp_dirname):
        shutil.rmtree(tmp_dirname)
        pd.del_data(id, "temp_db")
        pass

# I will assume that 3000 consecutive tweets will not have vanished by the time
#   we attempt to download images in the user's liked tweets again.
def load_from_file(id: str, limit: int = 3000, fnum: int = None) -> list[str]:
    """
    Loads the IDs of tweets into a list.

    Parameters
    ----------
    id: str
        The ID of the Twitter user.

    limit: int (optional)
        The number of tweet IDs to load. Maximum allowed length is 10 000, and
        minimum allowed is 1. Setting the limit to less than 1 or greater than
        10 000 will be corrected to 10 000.

        Default is 3000.

    fnum: int (optional)
        For internal use only.

    Returns
    -------
    list[str]
        A list of tweet IDs that the user has liked and has been processed,
        from the latest to the oldest. The length of this list should be equal
        to the limit, if a positive limit is set.
    """
    if id == None:
        raise ValueError("User ID required!")
    if not isinstance(limit, int):
        limit = 3000
    if limit < 1 or limit > 10000:
        limit = 10000

    if fnum == None:
        fnum = pd.get_data(id, "twt_db.file_num")
    if fnum < 1:
        return []

    fname = "%s%s.txt"%(futils.assemble_dir(id, "known_tweets", create=True), fnum)

    # This check should ideally never trigger after the first attempt to fetch
    # a user's liked tweets.
    if not os.path.exists(fname):
        if fnum > 1:
            raise RuntimeError("Record of liked tweets for user ID " +
                "%s may require repairs!"%(id))
        return []

    twts = []
    count = 0
    reverse_gen = futils.readline_reverse(fname)
    for l in reverse_gen:
        if count >= limit > 0:
            break
        if l in twts:
            continue
        twts.append(l)
        count += 1

    reverse_gen.close()
    if limit < 1:
        twts.extend(load_from_file(id, limit, fnum - 1))
    elif limit > count:
        twts.extend(load_from_file(id, limit - count, fnum - 1))

    return twts

def _save_explicit(id, twts, limit = 5000, fnum = None, twtslen = None):
    if fnum == None:
        fnum = pd.get_data(id, "twt_db.file_num", default=1)
    if twtslen == None:
        twtslen = len(twts)
    if twtslen <= 0:
        return

    lcount = pd.get_data(id, "twt_db.line_count", index = fnum - 1, default=0)
    fname = "%s%s.txt"%(futils.assemble_dir(id, "known_tweets", create=True), fnum)
    count = 0

    if (count + lcount) < limit:
        with open(fname, "a") as f:
            for t in twts:
                if (count + lcount) >= limit:
                    break
                f.write(str(t) + "\n")
                count += 1

    pd.set_data(id, "twt_db.line_count", index=fnum - 1,
            set_func=(lambda x: count if x == None else x + count))
    if lcount + twtslen > limit:
        fnum_next = fnum + 1
        pd.set_data(id, "twt_db.file_num", fnum_next)
        _save_explicit(id, twts[count:], limit, fnum_next, twtslen - count)

def _combine_saves_with_temp(id, limit = 5000):
    for l in _revolve_temp_files(id):
        _save_explicit(id, l, limit)

def _revolve_temp_files(id: str):
    if id == None:
        raise ValueError("User ID required!")

    tmp_dir = futils.assemble_dir(id, "known_tweets", "temp")
    if not os.path.exists(tmp_dir):
        return

    fnum = pd.get_data(id, "temp_db.file_num", default=0)
    while fnum >= 1:
        fname = "%s%s.txt"%(tmp_dir, fnum)
        if os.path.exists(fname):
            res = []
            with open(fname, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        res.append(line)
            yield res

        fnum -= 1
