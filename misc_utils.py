import datetime

def add_one(x):
    return x + 1

def index_of_last_slash(str_val: str) -> int:
    fs = str_val.rfind("/")
    bs = str_val.rfind("\\")
    return max(fs, bs)

def today(only_numeric: bool = False) -> str:
    """
    Fetches the current date.

    Parameters
    ----------
    only_numeric: bool
        Determines how to format the date.

        Default is False.

    Returns
    -------
    str
        Returns date formatted as YYYY-MM-DD if only_numeric is False,
        YYYYMMDD otherwise.
    """
    val = str(datetime.date.today())
    return val.replace("-", "") if only_numeric else val

def is_sublist(biglist: list, sublist: list) -> bool:
    """
    Compares two lists to see if one is contained in the other.

    Parameters
    ----------
    biglist: list
        The larger list.

    sublist: list
        The sublist.

    Returns
    -------
    bool
        Whether sublist is contained inside of biglist.
    """
    for i in sublist:
        if i not in biglist:
            return False
    return True

def isiterable(obj):
    try:
        dummy = (e for e in obj)
        return True
    except TypeError:
        return False

def printv(*values: object,
        sep: str = None,
        end: str = None,
        verbose: bool =True):
    """
    A wrapper that prevents print from being executed if verbose isn't enabled.
    The only extra argument is "verbose", which accepts boolean values.
    """
    if verbose:
        print(*values, sep = sep, end = end)
