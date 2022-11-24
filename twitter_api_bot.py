import re
import json
import requests

import misc_utils as mutils

"""
Custom errors
"""

class RequestCountError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            print(self.message)
        else:
            print("The number of requests made to the Twitter API exceeded the maximum allowed " +
                    "amount!")

class UnsuccessfulRequestError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            print(self.message)
        else:
            print("Status code received from a request was not 200!")



"""
Important vars
"""

# Maximum requests to make to the Twitter API at once before aborting execution
max_requests = 50
requests_count = 0



"""
Fetch credentials from local JSON file
"""

creds = None
with open("creds.json","r") as cfile:
    creds = json.load(cfile)
if creds == None:
    raise RuntimeError("Credentials in file could not be loaded.")



"""
Base API methods
"""

def user_id_url(*usernames: str) -> str:
    """
    Generates a Twitter API v2 URL to fetch a user's ID based on a username.

    Parameters
    ----------
    usernames: str
        The usernames of the Twitter users. Not to be confused with display
        names.

    Returns
    -------
    str
        A Twitter API v2 URL, or an empty string if no usernames are provided.
    """
    if len(usernames) == 0:
        return ""

    output = usernames[0]
    for u in usernames[1:]:
        output += ("," + u)
    return "https://api.twitter.com/2/users/by?usernames=" + output

def liked_tweets_url(id: str, expansions: str = None, tweet_fields: str = None,
        user_fields: str = None, media_fields:str = None,
        page_token: str = None) -> str:
    """
    Generates a Twitter API v2 URL to fetch a user's liked tweets. Behavior is
    modified based on a few parameters.

    Parameters
    ----------
    id: str
        The ID of the Twitter user.

    expansions: str (optional)
        The "expansions" field of the Twitter API v2 request URL.

        Default is None.

    tweet_fields: str (optional)
        The "tweet_fields" field of the Twitter API v2 request URL.

        Default is None.

    user_fields: str (optional)
        The "user_fields" field of the Twitter API v2 request URL.

        Default is None.

    media_fields: str (optional)
        The "media_fields" field of the Twitter API v2 request URL.

        Default is None.

    page_token: str (optional)
        The pagination token to use.

        Default is None.

    Returns
    -------
    str
        A Twitter API v2 URL.
    """
    url_end = "%s/liked_tweets"%(id)
    decorations = []
    if expansions != None:
        decorations.append("expansions=%s"%(expansions))
    if tweet_fields != None:
        decorations.append("tweet.fields=%s"%(tweet_fields))
    if user_fields != None:
        decorations.append("user.fields=%s"%(user_fields))
    if media_fields != None:
        decorations.append("media.fields=%s"%(media_fields))
    if page_token != None:
        decorations.append("pagination_token=%s"%(page_token))

    decor_len = len(decorations)
    if decor_len != 0:
        url_end += "?"
        for i in range(decor_len):
            url_end += decorations[i] + ("&" if i < decor_len - 1 else "")
    url = "https://api.twitter.com/2/users/" + url_end
    #print(url)
    return url

def bearer_oauth(r):
    """
    Sets authorization tokens based on a bearer token as provided by the
    Twitter API.

    To be passed as an argument like so:
        requests.request(..., auth=bearer_oauth)
    """
    r.headers["Authorization"] = "Bearer %s"%(creds["bearer_token"])
    r.headers["User-Agent"] = "LikeDownloaderForSelf"
    return r

def connect_to_endpoint(url: str) -> dict:
    """
    Connects to the Twitter API v2 using the given URL. Automatically passes
    the method bearer_oauth(r) to requests.request(...).

    Parameters
    ----------
    url: str
        The Twitter API v2 URL to fetch a response from.

    Raises
    ------
    Exception
        If the status code given by the request isn't 200, this exception is
        raised.

    Returns
    -------
    dict
        A dict representing the JSON response given.
    """
    global requests_count
    if requests_count >= max_requests:
        raise RequestCountError()

    response = requests.request("GET", url, auth=bearer_oauth)
    #print(response.status_code)
    if response.status_code != 200:
        err_msg = "Request returned an error: %s %s"%(response.status_code, response.text)
        raise UnsuccessfulRequestError(err_msg)

    requests_count += 1
    return response.json()



"""
Fetch methods
"""

def fetch_user_ids(*usernames: str) -> list[str]:
    """
    Returns the IDs of a list of Twitter users. Increases request count by 1.

    Parameters
    ----------
    usernames: str
        The usernames of the Twitter users. Not to be confused with display
        names.

    Raises
    ------
    Exception
        If the number of requests has already exceeded the maximum number of
        requests allowed by this program.

    Returns
    -------
    list[str]
        A list of IDs for each username, in order.
    """
    url = user_id_url(*usernames)
    if not url:
        return []

    api_response = connect_to_endpoint(url)
    return [usr["id"] for usr in api_response["data"]]

def fetch_liked_tweets(usr_id: str, *, expansions: str = None,
        tweet_fields: str = None, user_fields: str = None,
        media_fields:str = None, page_token: str = None,
        verbose: bool = True):
    """
    A generator that yields a page of liked tweets with each call. Each page
    is a dict representation of the JSON response from the Twitter API.

    Please note that in order to use this generator, you will be required to
    use the next() function. For example:
    >   liked_tweet_generator = fetch_liked_tweets(0)
    >   page_of_tweets = next(liked_tweet_generator)

    Parameters
    ----------
    usr_id: str
        The ID of the Twitter user.

    expansions: str (optional)
        The "expansions" field of the Twitter API v2 request URL.

        Default is None.

    tweet_fields: str (optional)
        The "tweet_fields" field of the Twitter API v2 request URL.

        Default is None.

    user_fields: str (optional)
        The "user_fields" field of the Twitter API v2 request URL.

        Default is None.

    media_fields: str (optional)
        The "media_fields" field of the Twitter API v2 request URL.

        Default is None.

    page_token: str (optional)
        The pagination token provided by a previous call to Twitter's API.

        Defaults to None.

    verbose: bool (optional)
        Whether or not to allow verbose debugging.

        Defaults to True.
    """
    __page_token = page_token
    while True:
        url = liked_tweets_url(id=usr_id, expansions=expansions, tweet_fields=tweet_fields,
            user_fields=user_fields, media_fields=media_fields, page_token=__page_token)
        api_response = connect_to_endpoint(url)

        if "data" in api_response:
            yield api_response
        else:
            mutils.printv("Response returned no data.", verbose=verbose)
            break

        if "next_token" in api_response["meta"]:
            __page_token = api_response["meta"]["next_token"]
        else:
            mutils.printv("Reached end of liked tweets.", verbose=verbose)
            break



"""
"External URL" detector
"""

external_urls = {}

def reg_external_url(id: str, tweet: dict, usr_dict: dict):
    """
    Checks a tweet and, if it has possibly external URLs, remember it in order
    to inform the user of the existence of such tweets later.

    Parameters
    ----------
    id: str
        The ID of the Twitter user to associate the external URLs to.

    tweet: dict
        A JSON representation of a Tweet, provided by the Twitter API.

    usr_dict: dict
        A dict mapping Twitter user IDs to @usernames.
    """
    if not check_for_external_urls(tweet):
        return

    global external_urls
    author = usr_dict[tweet["author_id"]]
    tweet_id = tweet["id"]
    url = "https://twitter.com/%s/status/%s"%(author, tweet_id)

    if id not in external_urls:
        external_urls[id] = []
    external_urls[id].append(url)

def check_for_external_urls(tweet: dict):
    """
    Searches a tweet for any external URLs by relying on the Twitter API's
    "entities" field.

    Parameters
    ----------
    tweet: dict
        The tweet to scrub. Should be retrieved directly from the JSON response
        given by the Twitter API.

    Returns
    -------
    bool
        True if a potential external URL was found, false otherwise.
    """
    if "entities" not in tweet or "urls" not in tweet["entities"]:
        return False

    regex_pattern = "^https://twitter\.com/"
    url_tc = tweet["entities"]["urls"]

    for url_obj in url_tc:
        if not re.search(regex_pattern, url_obj["expanded_url"]):
            return True
    return False

def dump_all_external_urls():
    """
    Dumps all tweets with possible external URLs to a file. If no external URLs
    were detected, this does nothing.

    Parameters
    ----------
    id: str
        The ID of the Twitter user to associate the external URLs to.
    """
    for k in external_urls.keys():
        dump_external_urls_for_usr(k)

def dump_external_urls_for_usr(id: str):
    if id not in external_urls:
        return
    urls = external_urls[id]
    ucount = len(urls)
    if ucount == 0:
        return

    filepath = "./%s/external_urls.txt"%(id)
    with open(filepath, "a") as f:
        f.write(mutils.today() + "\nThe following URLs have possible external URLs:")
        for u in urls:
            f.write("\n" + u)
        f.write("\n\n")
