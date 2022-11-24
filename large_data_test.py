import persistent_data as pd
import known_tweets_handler as kth

def main():
    # Save test
    pd.load_from_file("test_id")
    #kth.save_temp("test_id", [i - 100 for i in range(100)])
    kth.save_to_file("test_id", [i for i in range(10000)])
    pd.save_to_file()

    # Load test
    loaded = kth.load_from_file("test_id", 2000)
    print(loaded[:100], loaded[-100:], len(loaded), loaded[0], loaded[-1], sep=" :: ")
    loaded = kth.load_from_file("test_id", 0)
    print(loaded[:100], loaded[-100:], len(loaded), loaded[0], loaded[-1], sep=" :: ")


if __name__ == "__main__":
    main()
