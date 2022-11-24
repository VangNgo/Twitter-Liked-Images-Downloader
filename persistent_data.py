import os
import json

"""
Class
"""

class DataWrapper():
    """
    A dict wrapper to handle "complicated" procedures.
    """

    # Static functions
    @staticmethod
    def default_vals():
        return {
            "twt_db": {
                "file_num": 1,
                "line_count": []
            },
            "liked_tweets": {
                "count": 0,
                "with_external_urls": 0
            },
            "imgs_downloaded": 0,
            "requests_made": 0,
        }

    @staticmethod
    def _detect_dw(dict_obj):
        for k, v in dict_obj:
            if isinstance(v, dict):
                if DataWrapper._detect_dw(v):
                    return True
            if isinstance(v, DataWrapper):
                return True
        return False


    # Instance functions
    def __init__(self, settings = None):
        if isinstance(settings, dict):
            self._d = settings
        elif isinstance(settings, DataWrapper):
            self._d = settings._d
        else:
            self._d = DataWrapper.default_vals()

    def _get(self, key, default = None):
        try:
            fdest, fkey = self._traverse(key)
            return fdest[fkey]
        except KeyError as e:
            if default != None:
                return default
            raise e

    def _get_in_list(self, key, index, default = None):
        try:
            fdest, fkey = self._traverse(key)
            get_list = fdest[fkey]

            if not isinstance(get_list, list):
                raise ValueError("Data set at \"" + key + "\" is not a list!")
            return get_list[index]
        except (KeyError, IndexError) as e:
            if default != None:
                return default
            raise e

    def overwrite(self, new_settings):
        if isinstance(new_settings, dict):
            self._d = new_settings
        elif isinstance(new_settings, DataWrapper):
            self._d = new_settings._d
        else:
            raise ValueError("DataWrapper or dict required!")

    # This should NOT be called directly! Please use the following non-class,
    # non-instance method instead: set_data_for_id(str, any, any, *, int, callable)
    def _set(self, key, val = None, set_func = None):
        if isinstance(val, DataWrapper):
            raise ValueError("Cannot put a DataWrapper in a DataWrapper!")
        fdict, fkey = self._traverse(key, True)
        prev_val = None if fkey not in fdict else fdict[fkey]

        if set_func != None and callable(set_func):
            val = set_func(prev_val)
        if val in [None, prev_val]:
            return False
        fdict[fkey] = val
        return True

    def _del(self, key):
        fdict = None
        fkey = None
        try:
            fdict, fkey = self._traverse(key)
            if fkey in fdict:
                del fdict[fkey]
                return True
        except KeyError:
            pass
        return False


    # This should NOT be called directly! Please use the following non-class,
    # non-instance method instead: set_data_for_id(str, any, any, *, int, callable)
    def _set_in_list(self, key, index, val = None, set_func = None):
        fdict, fkey = self._traverse(key, True)
        orig_list = [] if fkey not in fdict else fdict[fkey]

        if not isinstance(orig_list, list):
            raise ValueError("Data set at \"" + key + "\" is not a list!")

        orig_len = len(orig_list)
        need_append = False
        work_index = index
        work_list = orig_list
        if orig_len <= index:
            need_append = True
            work_list = [None for i in range(index - orig_len + 1)]
            work_index = index - orig_len

        if set_func != None and callable(set_func):
            val = set_func(work_list[work_index])
        if val in [None, work_list[work_index]]:
            return False

        work_list[work_index] = val

        if need_append:
            orig_list.extend(work_list)
        fdict[fkey] = orig_list
        return True

    def _traverse(self, key, create = False):
        if not isinstance(key, str):
            return self._d, key
        subdict = self._d
        klist = key.split(".")

        if len(klist) == 1:
            return self._d, key

        for kpart in klist[0:-1]:
            if not isinstance(subdict, dict):
                typeget = str(type(subdict))
                tq1 = typeget.find("'")
                tq2 = typeget.find("'", tq1 + 1) + 1
                raise KeyError("Key cannot be retrieved from objects of type " + typeget[tq1:tq2])
            if create and kpart not in subdict:
                subdict[kpart] = {}
            subdict = subdict[kpart]
        fdict = subdict
        fkey = klist[-1]
        return fdict, fkey

    def __str__(self):
        return json.dumps(self._d)



"""
Variables
"""

_loaded_data = {}
_data_modified = []



"""
Main
"""

def get_data(id: str, key = None, index = None, default = None):
    """
    Retrieves data related to the given ID.

    Parameters
    ----------
    id: str
        The ID to fetch data for.

    key (optional)
        The key to retrieve data for.

        Default is None.

    Returns
    -------
    any
        A dict containing all data for the ID if the key is set to None.
        Otherwise, returns the data associated with the specified key.
    """
    if id == None:
        raise ValueError("User ID required!")

    global _loaded_data
    _default_if_nonexistent(id)

    if key == None:
        return _loaded_data[id]
    if index == None:
        return _loaded_data[id]._get(key, default)
    return _loaded_data[id]._get_in_list(key, index, default)

def set_data(id: str, key, val = None, *, index = None, set_func = None) -> bool:
    """
    Sets data for the specified ID.

    Parameters
    ----------
    id: str
        The ID to set data for.

    key
        The key to set data for.

    val (optional)
        The new value for the key.

    set_func: function (optional)
        A function to pass the old value to.

    Returns
    -------
    bool
        True if the new value was successfully set, False otherwise. A value of
        None will return False, and the data will not be changed.
    """
    if None in [id, key]:
        raise ValueError("User ID and key name required!")

    if isinstance(index, int):
        dset = get_data(id)._set_in_list(key, index, val, set_func)
    else:
        dset = get_data(id)._set(key, val, set_func)
    if dset:
        _set_as_modified(id)
    return dset

def del_data(id: str, key):
    """

    """
    if id == None:
        raise ValueError("User ID required!")

    if key == None:
        if id in _loaded_data:
            del _loaded_data[id]
            return True
        return False

    return _loaded_data[id]._del(key)

def load_from_file(id: str):
    """
    Loads data for the given ID from file.
    """
    if id == None:
        raise ValueError("User ID required!")

    global _loaded_data
    fp = _get_file(id)
    data = None

    if not os.path.exists(fp):
        if id not in _loaded_data:
            _default_if_nonexistent(id)
        return

    with open(fp, "r") as f:
        data = json.load(f)
    _loaded_data[id] = DataWrapper(data)

def save_to_file():
    """
    Saves all modified data to file.
    """
    for id in _data_modified:
        fp = _get_file(id)
        with open(fp, "w") as f:
            json.dump(_loaded_data[id]._d, f)

def _get_file(id: str):
    return "./%s/persistent_data.json"%(id)

def _default_if_nonexistent(id: str):
    global _loaded_data
    if id not in _loaded_data:
        _loaded_data[id] = DataWrapper()
        _set_as_modified(id)

def _set_as_modified(id: str):
    global _data_modified
    if id not in _data_modified:
        _data_modified.append(id)
