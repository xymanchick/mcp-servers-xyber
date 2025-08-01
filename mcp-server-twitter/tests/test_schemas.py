import pytest
from pydantic import ValidationError

from mcp_server_twitter.schemas import (
    CreateTweetInput,
    FollowUserInput,
    GetTrendsInput,
    GetUserTweetsInput,
    RetweetTweetInput,
    SearchHashtagInput,
)

# === CreateTweetInput ===


def test_create_tweet_valid():
    data = {
        "text": "Hello world!",
        "poll_options": ["a", "b"],
        "poll_duration": 60,
    }
    model = CreateTweetInput(**data)
    assert model.text == "Hello world!"


def test_create_tweet_invalid_text_too_short():
    with pytest.raises(ValidationError):
        CreateTweetInput(text="", poll_options=["a", "b"], poll_duration=60)


def test_create_tweet_invalid_poll_options_too_few():
    with pytest.raises(ValidationError):
        CreateTweetInput(text="Valid", poll_options=["a"])


# === GetUserTweetsInput ===


def test_get_user_tweets_valid():
    model = GetUserTweetsInput(user_ids=["1", "2"], max_results=50)
    assert model.max_results == 50


def test_get_user_tweets_invalid_max_results():
    with pytest.raises(ValidationError):
        GetUserTweetsInput(user_ids=["1"], max_results=999)


# === FollowUserInput ===


def test_follow_user_valid():
    model = FollowUserInput(user_id="abc")
    assert model.user_id == "abc"


def test_follow_user_empty_user_id():
    with pytest.raises(ValidationError):
        FollowUserInput(user_id="")


# === RetweetTweetInput ===


def test_retweet_valid():
    model = RetweetTweetInput(tweet_id="xyz")
    assert model.tweet_id == "xyz"


def test_retweet_invalid():
    with pytest.raises(ValidationError):
        RetweetTweetInput(tweet_id="")


# === GetTrendsInput ===


def test_get_trends_valid():
    model = GetTrendsInput(countries=["USA"], max_trends=5)
    assert model.max_trends == 5


def test_get_trends_invalid():
    with pytest.raises(ValidationError):
        GetTrendsInput(countries="USA", max_trends=999)


# === SearchHashtagInput ===


def test_search_hashtag_valid():
    model = SearchHashtagInput(hashtag="#test", max_results=25)
    assert model.hashtag == "#test"


def test_search_hashtag_invalid():
    with pytest.raises(ValidationError):
        SearchHashtagInput(hashtag="", max_results=200)
