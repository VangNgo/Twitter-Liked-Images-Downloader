# Twitter-Liked-Images-Downloader
Attempts to download images attached to a user's liked tweets while providing
extra information where appropriate.

## Setup

Download all files to the same folder, then create the file `creds.json` in the
same folder. The contents of `creds.json` should appear as so:

```json
{
    "consumer_key": "XXXXX",
    "consumer_secret": "XXXXX",
    "bearer_token": "XXXXX",

    "access_token": "XXXXX",
    "access_secret": "XXXXX"
}
```

## Using the script

To use, open the command prompt and run:

```bat
py download_liked_tweets.py -u "TWITTER_USERNAME"
```

### All command line arguments

`-u` / `--user`
> The Twitter handle of the user. This is the only required argument.
>
> *Requires value:* Yes
>
> *Example usage:*
> ```bat
> py download_liked_tweets.py -u "TWITTER_USERNAME"
> ```

---

`-f` / `--folder`
> The folder to save the downloaded images to. Defaults to `./USER_ID/downloaded_tweets/`
>
> *Requires value:* Yes
>
> *Example usage:*
> ```bat
> py download_liked_tweets.py -u "TWITTER_USERNAME" -f "my custom folder"
> ```

---

`-p` / `--page-token`
> The pagination token as provided by the Twitter API.
>
> *Requires value:* Yes
>
> *Example usage:*
> ```bat
> py download_liked_tweets.py -u "TWITTER_USERNAME" -p "000000"
> ```

---

`-i` / `--ignore-processed`
> Sets whether to ignore tweets that the script has already processed. This
> option is not recommended for use.
>
> *Requires value:* No
>
> *Example usage:*
> ```bat
> py download_liked_tweets.py -u "TWITTER_USERNAME" -i
> ```

---

`-v` / `--verbose`
> Sets whether to enable verbose output.
>
> *Requires value:* No
>
> *Example usage:*
> ```bat
> py download_liked_tweets.py -u "TWITTER_USERNAME" -v
> ```

## Information saved

In the `USER_ID/persistent_data.json` file, the following statistics are saved:
- Information related to the pseudo-"database" of tweet IDs indicating the
tweets that the script has already processed for the given user.
- The total number of tweets the user has liked.
- The total number of tweets that has URLs that do not use the `twitter.com`
domain.
- The total number of images downloaded.
- The total amount of requests made to the Twitter API v2.

In general, this file should not be manually edited. The information saved is
reused and updated by the script every execution.

In the event that a tweet is found to have links pointed to an external site,
a list of direct URLs to the tweets will be saved in
`USER_ID/external_urls.txt`.

## Disclaimers

First, I would like to remark that this was my first exploration into trying
to handle large amounts of data. To begin, I assumed the following:
1. The Twitter API v2 is operational.
2. No more than 10,000 of the user's latest liked tweets would be deleted at
once.
3. The users being processed will not have liked so many tweets that an obscene
number of files are created by [this module](https://github.com/VangNgo/Twitter-Liked-Images-Downloader/blob/main/known_tweets_handler.py).
By obscene, I imagine at least a thousand "database" files before attempting to
load the user's persistent data becomes cumbersome.

There are still factors I did not account for at the time of writing this
README.
1. I did not implement a failsafe in the event that the script tries to process
an obscene number of tweets. In which case, memory may be a problem with
regards to saving the list of new tweet IDs to save as "processed." The
variable of interest is [here](https://github.com/VangNgo/Twitter-Liked-Images-Downloader/blob/1f0455f9d64c01d67268c38270b2c5e41a54dda9/download_liked_tweets.py#L96).
2. In a similar vein, I assumed that the vast majority of liked tweets will not
have external URLs. As a result, there is the potential that memory will be
a problem if a user has liked thousands of tweets that all have external URLS.
The variable of interest is [here](https://github.com/VangNgo/Twitter-Liked-Images-Downloader/blob/1f0455f9d64c01d67268c38270b2c5e41a54dda9/twitter_api_bot.py#L305).

An additional known weakness is that all external URLs are saved to a single
file. This may make the file difficult or impossible to open if a great number
of tweet URLs are saved.

Furthermore, I did not test this script against a user with a number of liked
tweets required to ensure that this script can, in fact, process a large amount
of data. I tested the [known_tweets_handler](https://github.com/VangNgo/Twitter-Liked-Images-Downloader/blob/main/known_tweets_handler.py)
module against a smaller set of test data, namely:

```py
import persistent_data as pd
import known_tweets_handler as kth

# Save 10100 numbers. Should be split across 3 files.
pd.load_from_file("test_id")
kth.save_temp("test_id", [i - 100 for i in range(100)])
kth.save_to_file("test_id", [i for i in range(10000)])
pd.save_to_file()

# Loads the data back in.
loaded = kth.load_from_file("test_id", 2000)
# Debug the loaded data to ensure that it returns the expected values
# print(loaded[:100], loaded[-100:], len(loaded), loaded[0], loaded[-1], sep=" :: ")
loaded = kth.load_from_file("test_id", 0)
# Debug the loaded data to ensure that it returns the expected values
# print(loaded[:100], loaded[-100:], len(loaded), loaded[0], loaded[-1], sep=" :: ")
```

In the future, if I decide to improve this script, I will attempt to handle
the current weaknesses of the script. In particular, I want to make use of
`known_tweets_handler.save_temp(str, list)` and implement a better, more
efficient method of reading and saving the data of interest.
