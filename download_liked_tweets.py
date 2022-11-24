import requests
import sys
import getopt
import shutil

import file_utils as futils
import misc_utils as mutils
import persistent_data as pd
import known_tweets_handler as kth
import twitter_api_bot as twab

"""
Credential loading
"""

# Fetch credential information from "creds.json"
# We want the program to fail completely if credentials cannot be loaded, and
#   moreover if it doesn't follow this specific format:
#   {
#       "consumer_key": "CONSUMER_ACCESS_KEY",
#       "consumer_secret": "CONSUMER_SECRET_KEY",
#       "bearer_token": "BEARER_OAUTH_TOKEN",
#       "access_token": "ACCESS_TOKEN",
#       "access_secret": "ACCESS_SECRET_KEY"
#   }
creds = futils.import_json("creds.json")
creds_keylist = ["consumer_key",
        "consumer_secret",
        "bearer_token",
        "access_token",
        "access_secret"]

if not isinstance(creds, dict) or not mutils.is_sublist(list(creds.keys()), creds_keylist):
    raise RuntimeError("Credentials file not valid.")



"""
File-related
"""

def gen_img_filename(twt_author: str, url: str, extra: str = None) -> str:
    """
    Generates a filename based on Twitter authors, a date, and a URL.

    Parameters
    ----------
    twt_author: str
        The username of the Twitter user who authored the tweet.

    url: str
        A date. It is recommended to have this as the creation date of the
        tweet.

    extra: str (optional)
        Extra information to append to the end of the file name, before the
        file extension. If not set to either None or "", an underscore will be
        added to separate the main filename from the extra data.

        Default is None.

    Returns
    -------
    str
        A filename incorporating the above parameters. Output should appear as:
                (#1)[twitter]#2_#3.#4,
        where
            #1: author_name
            #2: part of the URL before the file extension and after the final
                slash
            #3: extra information
            #4: file extension

        If no extra information is given, then _#3 is removed from the final
        output.
    """
    last_slash = url.rfind("/")
    last_dot = min([len(url), url.rfind(".")])
    img_id = url[last_slash + 1:last_dot].replace("-", "").replace("_", "")
    img_ext = url[last_dot + 1:]

    fname = "(%s)[twitter]%s"%(twt_author, img_id)
    if extra:
        fname += "_%s"%(extra)

    return fname + "." + img_ext



"""
Specialized data
"""

is_verbose = False
processed_tweets = []
new_processed_tweets = []

def gen_id2usr(api_response: dict) -> dict:
    """
    Overwrites the global variable id2usr_dict with a new dict mapping Twitter
    user IDs to @usernames based on the given JSON response from the Twitter
    API.

    Parameters
    ----------
    json_obj : dict
        A dict representing a JSON object. Should be a full response from the
        Twitter API.
    """
    if "includes" not in api_response or "users" not in api_response["includes"]:
        return {}

    usr_list = api_response["includes"]["users"]
    return {u["id"]: u["username"] for u in usr_list}

def gen_media2url(api_response: dict) -> dict:
    """
    Overwrites the global variable media2url_dict with a new dict mapping IDs
    of media files to their direct URLs based on the given JSON response from
    the Twitter API.

    Parameters
    ----------
    json_obj : dict
        A dict representing a JSON object. Should be a full response from the
        Twitter API.

    Returns
    -------
    dict
        A dict mapping media IDs (str) to URLs (str).
    """
    if "includes" not in api_response and "media" not in api_response["includes"]:
        return {}

    media_list = api_response["includes"]["media"]
    mk, u, t, p = ("media_key", "url", "type", "photo")
    return {m[mk]: m[u] for m in media_list if m[t] == p}



"""
Major methods
"""

def download_img(url: str, fname: str, tweet_url = None):
    """
    Downloads an image from the given URL and saves it to the filepath.

    Parameters
    ----------
    url: str
        The URL to download an image from.

    fname: str
        The filepath to save the image to.
    """
    i_res = requests.get(url, stream=True)
    if i_res.status_code == 200:
        with open(fname, "wb") as f:
            shutil.copyfileobj(i_res.raw, f)
        mutils.printv("Image downloaded: %s"%(fname), verbose=is_verbose)
        return True

    err_msg = "Image could not be retrieved: URL(%s)"%(url)
    if tweet_url != None:
        err_msg += " TWEET(%s)"%(tweet_url)
    mutils.printv(err_msg, verbose=is_verbose)
    return False

def process_usr_for_liked(usr_id, folder: str, page_token: str = None,
        ignore_processed: bool = False) -> tuple[bool, int]:
    """
    Continuously reaches out to the Twitter API in an attempt to retrieve all
    of the given user ID's liked tweets.

    If any liked tweet contains an image, that image will be downloaded. If the
    tweet has a URL that is potentially external, we will also save information
    about those tweets for future reference.

    References
    ----------
    usr_id
        The Twitter user's ID.

    folder: str
        The folder to save the images to.

    page_token: str (optional)
        The pagination token to use. Defaults to None.

    ignore_processed: bool (optional)
        Whether to disregard the information we have regarding processed tweets.
        Defaults to False.

    Returns
    -------
    bool, int
        Returns whether the operation was prematurely halted, along with a
        count detailing the number of images downloaded.
    """
    halt = img_count = tweet_count = 0
    next_token = page_token
    try:
        liked_tweets = twab.fetch_liked_tweets(usr_id,
                expansions="author_id,attachments.media_keys",
                tweet_fields="created_at,entities", media_fields="url",
                page_token=next_token)

        while (api_response := next(liked_tweets, None)) != None:
            halt, imgs, tweets = process_response_for_imgs(usr_id, api_response, folder, ignore_processed)
            if is_verbose:
                mutils.printv("Fetched page of tweets with token %s..."%(next_token),
                        verbose=(is_verbose and next_token != None))
                if "next_token" in api_response["meta"]:
                    next_token = api_response["meta"]["next_token"]
            img_count += imgs
            tweet_count += tweets
            if halt > 0:
                break
    except twab.UnsuccessfulRequestError:
        halt = 1

    return halt, img_count, tweet_count

def process_response_for_imgs(usr_id, api_response: dict, folder: str,
        ignore_processed: bool = False) -> tuple[bool, int]:
    """
    Processes the data from a JSON web response. If images are detected, an
    attempt will be made to download them.

    Parameters
    ----------
    json_obj: dict
        The JSON response from a Twitter API v2 request.

    folder: str
        The folder to save images to.

    Returns
    -------
    bool, int
        A bool indicating if the processing was prematurely halted for any
        reason; and an int indicating the number of images downloaded.
    """
    if "data" not in api_response:
        return 0, 0

    global processed_tweets, new_processed_tweets

    halt = img_count = tweet_count = 0
    id2usr = gen_id2usr(api_response)
    media2url = gen_media2url(api_response)

    for tweet in api_response["data"]:
        if "attachments" not in tweet or "media_keys" not in tweet["attachments"]:
            continue

        tweet_id = tweet["id"]
        if (not ignore_processed) and tweet_id in processed_tweets:
            halt = 2
            break

        img_count += process_tweet_for_media(tweet, id2usr, media2url, folder)
        new_processed_tweets.append(tweet_id)
        tweet_count += 1

        if "entities" in tweet and "urls" in tweet["entities"] and twab.reg_external_url(usr_id, tweet, id2usr):
            pd.set_data(usr_id, "liked_tweets.with_external_urls", set_func=mutils.add_one)

    return halt, img_count, tweet_count

def process_tweet_for_media(tweet: dict, id2usr: dict, media2url: dict, folder: str = None):
    if not isinstance(folder, str):
        folder = "./"
    img_count = 0
    author = id2usr[tweet["author_id"]]
    tweet_url ="https://twitter.com/%s/status/%s"%(author, tweet["id"])
    for key in tweet["attachments"]["media_keys"]:
        if key not in media2url:
            continue

        img_url = media2url[key]
        date = tweet["created_at"][:10].replace("-", "")
        filename = folder + gen_img_filename(author, img_url, date)
        if download_img(img_url, filename, tweet_url):
            img_count += 1

    return img_count



"""
Command line execution
"""

def main(username, folder = None, page_token = None, ignore_processed = False, verbose = False):
    global processed_tweets, new_processed_tweets, is_verbose

    is_verbose = verbose
    usr_id = twab.fetch_user_ids(username)[0]
    processed_tweets = kth.load_from_file(usr_id)

    if not isinstance(folder, str):
        folder = "downloaded images"
    final_folder = futils.assemble_dir(usr_id, folder)

    halt, img_count, tweet_count = process_usr_for_liked(usr_id, final_folder, page_token, ignore_processed)

    pd.set_data(id, "liked_tweets.count", set_func=(lambda x: x + tweet_count))
    pd.set_data(id, "imgs_downloaded", set_func=(lambda x: x + img_count))
    pd.set_data(id, "requests_made", set_func=(lambda x: x + twab.requests_count))

    print("Total request count: %s/%s"%(twab.requests_count, twab.max_requests))
    print("Total images downloaded:", img_count)

    if halt > 0:
        print("Prematurely halted.", end=" ")
        if halt == 1:
            print("Request count exceeds maximum allowed (%s) in a single operation."%(twab.max_requests))
        elif halt == 2:
            print("Found a tweet we've already processed. Assuming all older tweets are also processed.")
        else:
            print("An unknown error has occurred.")

    twab.dump_external_urls_for_usr(usr_id)
    if id in twab.external_urls:
        mutils.printv("Found", len(twab.external_urls[id]), "external URLs.", verbose=is_verbose)

if __name__ == "__main__":
    user = None
    folder = None
    page_token = None
    ignore_processed = False
    verbose = False
    try:
        args, vals = getopt.getopt(
            sys.argv[1:],
            "u:f:p:iv",
            ["user=", "folder=", "page-token=", "ignore-processed", "no-verbose"]
        )

        a_num = 0
        for a, v in args:
            if a in ("-u", "--user"):
                user = v
            elif a in ("-f", "--folder"):
                folder = v
            elif a in ("-p", "--page-token"):
                page_token = v
            elif a in ("-i", "--ignore-processed"):
                ignore_processed = True
            elif a in ("-v", "--no-verbose"):
                verbose = True
    except getopt.error as err:
        print(str(err))
    if user == None:
        raise ValueError("A username is required!")
    main(user, folder, page_token, ignore_processed, verbose)
