import pytest
from mcp_server_twitter.schemas import (
    CreateTweetRequest,
    FollowUserRequest,
    GetTrendsRequest,
    GetUserTweetsRequest,
    RetweetTweetRequest,
    SearchHashtagRequest,
)
from pydantic_core import ValidationError as PydanticValidationError

# === CreateTweetRequest ===


def test_create_tweet_valid(common_test_data, schema_factories):
    """Test creating valid tweet with poll"""
    data = {
        "text": common_test_data["simple_text"],
        "poll_options": common_test_data["poll_options_min"],
        "poll_duration": common_test_data["standard_duration"],
    }
    model = CreateTweetRequest(**data)
    assert model.text == common_test_data["simple_text"]
    assert model.poll_options == common_test_data["poll_options_min"]
    assert model.poll_duration == common_test_data["standard_duration"]


def test_create_tweet_minimal(common_test_data):
    """Test creating tweet with only required field"""
    model = CreateTweetRequest(text=common_test_data["minimal_text"])
    assert model.text == common_test_data["minimal_text"]
    assert model.image_content_str is None
    assert model.poll_options is None
    assert model.poll_duration is None
    assert model.in_reply_to_tweet_id is None
    assert model.quote_tweet_id is None


def test_create_tweet_text_max_length(boundary_test_data):
    """Test tweet with maximum allowed length (280 chars)"""
    model = CreateTweetRequest(text=boundary_test_data["max_length_text"])
    assert model.text == boundary_test_data["max_length_text"]


def test_create_tweet_text_too_long(boundary_test_data):
    """Test tweet exceeding maximum length"""
    with pytest.raises(PydanticValidationError) as exc_info:
        CreateTweetRequest(text=boundary_test_data["over_max_text"])
    assert "String should have at most 280 characters" in str(exc_info.value)


def test_create_tweet_invalid_text_too_short(boundary_test_data, common_test_data):
    with pytest.raises(PydanticValidationError) as exc_info:
        CreateTweetRequest(
            text=boundary_test_data["empty_text"], 
            poll_options=common_test_data["poll_options_min"], 
            poll_duration=common_test_data["standard_duration"]
        )
    assert "String should have at least 1 character" in str(exc_info.value)


def test_create_tweet_with_image(common_test_data):
    """Test creating tweet with image content"""
    model = CreateTweetRequest(
        text=common_test_data["image_text"],
        image_content_str=common_test_data["base64_image"]
    )
    assert model.text == common_test_data["image_text"]
    assert model.image_content_str == common_test_data["base64_image"]


def test_create_tweet_with_reply(common_test_data):
    """Test creating reply tweet"""
    model = CreateTweetRequest(
        text=common_test_data["reply_text"],
        in_reply_to_tweet_id=common_test_data["reply_tweet_id"]
    )
    assert model.text == common_test_data["reply_text"]
    assert model.in_reply_to_tweet_id == common_test_data["reply_tweet_id"]


def test_create_tweet_with_quote(common_test_data):
    """Test creating quote tweet"""
    model = CreateTweetRequest(
        text=common_test_data["quote_text"],
        quote_tweet_id=common_test_data["quote_tweet_id"]
    )
    assert model.text == common_test_data["quote_text"]
    assert model.quote_tweet_id == common_test_data["quote_tweet_id"]


def test_create_tweet_poll_options_min(common_test_data):
    """Test poll with minimum allowed options (2)"""
    model = CreateTweetRequest(
        text=common_test_data["poll_question"],
        poll_options=common_test_data["poll_options_long"],
        poll_duration=common_test_data["standard_duration"]
    )
    assert len(model.poll_options) == 2


def test_create_tweet_poll_options_max(common_test_data):
    """Test poll with maximum allowed options (4)"""
    model = CreateTweetRequest(
        text=common_test_data["poll_question"],
        poll_options=common_test_data["poll_options_max"],
        poll_duration=common_test_data["standard_duration"]
    )
    assert len(model.poll_options) == 4


def test_create_tweet_invalid_poll_options_too_few(common_test_data):
    with pytest.raises(PydanticValidationError):
        CreateTweetRequest(
            text="Valid", 
            poll_options=common_test_data["poll_options_too_few"]
        )


def test_create_tweet_invalid_poll_options_too_many(common_test_data):
    """Test poll with too many options (>4)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        CreateTweetRequest(
            text=common_test_data["poll_question"],
            poll_options=common_test_data["poll_options_too_many"],
            poll_duration=common_test_data["standard_duration"]
        )
    assert "poll_options must contain between 2 and 4 items" in str(exc_info.value)


def test_create_tweet_poll_duration_min(common_test_data, schema_constants):
    """Test poll with minimum duration (5 minutes)"""
    model = CreateTweetRequest(
        text="Quick poll",
        poll_options=common_test_data["poll_options_yes_no"],
        poll_duration=schema_constants["min_poll_duration"]
    )
    assert model.poll_duration == schema_constants["min_poll_duration"]


def test_create_tweet_poll_duration_max(common_test_data, schema_constants):
    """Test poll with maximum duration (10080 minutes = 1 week)"""
    model = CreateTweetRequest(
        text="Long poll",
        poll_options=common_test_data["poll_options_yes_no"],
        poll_duration=schema_constants["max_poll_duration"]
    )
    assert model.poll_duration == schema_constants["max_poll_duration"]


def test_create_tweet_poll_duration_too_short(common_test_data, schema_constants):
    """Test poll with duration below minimum"""
    with pytest.raises(PydanticValidationError) as exc_info:
        CreateTweetRequest(
            text="Poll",
            poll_options=common_test_data["poll_options_min"],
            poll_duration=schema_constants["under_min_poll_duration"]
        )
    assert "Input should be greater than or equal to 5" in str(exc_info.value)


def test_create_tweet_poll_duration_too_long(common_test_data, schema_constants):
    """Test poll with duration above maximum"""
    with pytest.raises(PydanticValidationError) as exc_info:
        CreateTweetRequest(
            text="Poll",
            poll_options=common_test_data["poll_options_min"],
            poll_duration=schema_constants["over_max_poll_duration"]
        )
    assert "Input should be less than or equal to 10080" in str(exc_info.value)


def test_create_tweet_poll_options_without_duration():
    """Test that poll options can be provided without duration (uses default)"""
    model = CreateTweetRequest(
        text="Poll without duration",
        poll_options=["Yes", "No"]
    )
    assert model.poll_options == ["Yes", "No"]
    assert model.poll_duration is None


# === GetUserTweetsRequest ===


def test_get_user_tweets_valid(common_test_data):
    model = GetUserTweetsRequest(user_ids=["1", "2"], max_results=50)
    assert model.max_results == 50
    assert model.user_ids == ["1", "2"]


def test_get_user_tweets_default_max_results(common_test_data, schema_constants):
    """Test default max_results value"""
    model = GetUserTweetsRequest(user_ids=common_test_data["single_user_list"])
    assert model.max_results == schema_constants["user_tweets_default"]
    assert model.user_ids == common_test_data["single_user_list"]


def test_get_user_tweets_single_user(common_test_data):
    """Test with single user ID"""
    model = GetUserTweetsRequest(user_ids=common_test_data["single_user_list"], max_results=25)
    assert len(model.user_ids) == 1
    assert model.user_ids[0] == common_test_data["user_id"]


def test_get_user_tweets_multiple_users(common_test_data):
    """Test with multiple user IDs"""
    model = GetUserTweetsRequest(user_ids=common_test_data["multiple_users"], max_results=75)
    assert model.user_ids == common_test_data["multiple_users"]
    assert len(model.user_ids) == 3


def test_get_user_tweets_max_results_min(common_test_data, boundary_test_data):
    """Test with minimum max_results value (1)"""
    model = GetUserTweetsRequest(
        user_ids=common_test_data["single_user_list"], 
        max_results=boundary_test_data["user_tweets_boundaries"]["min"]
    )
    assert model.max_results == boundary_test_data["user_tweets_boundaries"]["min"]


def test_get_user_tweets_max_results_max(common_test_data, boundary_test_data):
    """Test with maximum max_results value (100)"""
    model = GetUserTweetsRequest(
        user_ids=common_test_data["single_user_list"], 
        max_results=boundary_test_data["user_tweets_boundaries"]["max"]
    )
    assert model.max_results == boundary_test_data["user_tweets_boundaries"]["max"]


def test_get_user_tweets_empty_user_ids(common_test_data):
    """Test with empty user_ids list"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetUserTweetsRequest(user_ids=common_test_data["empty_list"], max_results=10)
    assert "List should have at least 1 item" in str(exc_info.value)


def test_get_user_tweets_invalid_max_results(common_test_data, boundary_test_data):
    with pytest.raises(PydanticValidationError):
        GetUserTweetsRequest(
            user_ids=common_test_data["single_user_list"], 
            max_results=boundary_test_data["user_tweets_boundaries"]["over_max"]
        )


def test_get_user_tweets_max_results_zero():
    """Test with max_results = 0 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetUserTweetsRequest(user_ids=["user"], max_results=0)
    assert "Input should be greater than or equal to 1" in str(exc_info.value)


def test_get_user_tweets_max_results_negative():
    """Test with negative max_results (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetUserTweetsRequest(user_ids=["user"], max_results=-5)
    assert "Input should be greater than or equal to 1" in str(exc_info.value)


# === FollowUserRequest ===


def test_follow_user_valid(common_test_data):
    model = FollowUserRequest(user_id="abc")
    assert model.user_id == "abc"


def test_follow_user_numeric_id(common_test_data):
    """Test with numeric user ID as string"""
    model = FollowUserRequest(user_id=common_test_data["numeric_user_id"])
    assert model.user_id == common_test_data["numeric_user_id"]


def test_follow_user_alphanumeric_id(common_test_data):
    """Test with alphanumeric user ID"""
    model = FollowUserRequest(user_id=common_test_data["alphanumeric_user_id"])
    assert model.user_id == common_test_data["alphanumeric_user_id"]


def test_follow_user_empty_user_id():
    with pytest.raises(PydanticValidationError) as exc_info:
        FollowUserRequest(user_id="")
    assert "String should have at least 1 character" in str(exc_info.value)


def test_follow_user_whitespace_only():
    """Test with whitespace-only user_id (should be valid since it has length > 0)"""
    model = FollowUserRequest(user_id=" ")
    assert model.user_id == " "


# === RetweetTweetRequest ===


def test_retweet_valid():
    model = RetweetTweetRequest(tweet_id="xyz")
    assert model.tweet_id == "xyz"


def test_retweet_numeric_id():
    """Test with numeric tweet ID"""
    model = RetweetTweetRequest(tweet_id="123456789012345678")
    assert model.tweet_id == "123456789012345678"


def test_retweet_alphanumeric_id():
    """Test with alphanumeric tweet ID"""
    model = RetweetTweetRequest(tweet_id="tweet_123_abc")
    assert model.tweet_id == "tweet_123_abc"


def test_retweet_invalid():
    with pytest.raises(PydanticValidationError) as exc_info:
        RetweetTweetRequest(tweet_id="")
    assert "String should have at least 1 character" in str(exc_info.value)


def test_retweet_whitespace_only():
    """Test with whitespace-only tweet_id (should be valid since it has length > 0)"""
    model = RetweetTweetRequest(tweet_id=" ")
    assert model.tweet_id == " "


# === GetTrendsRequest ===


def test_get_trends_valid():
    model = GetTrendsRequest(countries=["USA"], max_trends=5)
    assert model.max_trends == 5
    assert model.countries == ["USA"]


def test_get_trends_default_max_trends():
    """Test default max_trends value"""
    model = GetTrendsRequest(countries=["Canada"])
    assert model.max_trends == 50
    assert model.countries == ["Canada"]


def test_get_trends_multiple_countries():
    """Test with multiple countries"""
    countries = ["USA", "Canada", "UK", "France", "Germany"]
    model = GetTrendsRequest(countries=countries, max_trends=25)
    assert model.countries == countries
    assert len(model.countries) == 5


def test_get_trends_max_trends_min():
    """Test with minimum max_trends value (1)"""
    model = GetTrendsRequest(countries=["USA"], max_trends=1)
    assert model.max_trends == 1


def test_get_trends_max_trends_max():
    """Test with maximum max_trends value (50)"""
    model = GetTrendsRequest(countries=["USA"], max_trends=50)
    assert model.max_trends == 50


def test_get_trends_empty_countries():
    """Test with empty countries list"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetTrendsRequest(countries=[], max_trends=10)
    assert "List should have at least 1 item" in str(exc_info.value)


def test_get_trends_invalid():
    with pytest.raises(PydanticValidationError):
        GetTrendsRequest(countries="USA", max_trends=999)


def test_get_trends_max_trends_zero():
    """Test with max_trends = 0 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetTrendsRequest(countries=["USA"], max_trends=0)
    assert "Input should be greater than or equal to 1" in str(exc_info.value)


def test_get_trends_max_trends_too_high():
    """Test with max_trends > 50 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetTrendsRequest(countries=["USA"], max_trends=51)
    assert "Input should be less than or equal to 50" in str(exc_info.value)


def test_get_trends_max_trends_negative():
    """Test with negative max_trends (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        GetTrendsRequest(countries=["USA"], max_trends=-5)
    assert "Input should be greater than or equal to 1" in str(exc_info.value)


# === SearchHashtagRequest ===


def test_search_hashtag_valid():
    model = SearchHashtagRequest(hashtag="#test", max_results=25)
    assert model.hashtag == "#test"
    assert model.max_results == 25


def test_search_hashtag_without_hash():
    """Test hashtag without # symbol"""
    model = SearchHashtagRequest(hashtag="python", max_results=50)
    assert model.hashtag == "python"


def test_search_hashtag_default_max_results():
    """Test default max_results value"""
    model = SearchHashtagRequest(hashtag="#coding")
    assert model.max_results == 10
    assert model.hashtag == "#coding"


def test_search_hashtag_max_results_min():
    """Test with minimum max_results value (10)"""
    model = SearchHashtagRequest(hashtag="#test", max_results=10)
    assert model.max_results == 10


def test_search_hashtag_max_results_max():
    """Test with maximum max_results value (100)"""
    model = SearchHashtagRequest(hashtag="#test", max_results=100)
    assert model.max_results == 100


def test_search_hashtag_alphanumeric():
    """Test with alphanumeric hashtag"""
    model = SearchHashtagRequest(hashtag="#python3", max_results=20)
    assert model.hashtag == "#python3"


def test_search_hashtag_with_underscore():
    """Test hashtag with underscore"""
    model = SearchHashtagRequest(hashtag="#machine_learning", max_results=30)
    assert model.hashtag == "#machine_learning"


def test_search_hashtag_empty():
    """Test with empty hashtag (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        SearchHashtagRequest(hashtag="", max_results=10)
    assert "String should have at least 1 character" in str(exc_info.value)


def test_search_hashtag_invalid():
    with pytest.raises(PydanticValidationError):
        SearchHashtagRequest(hashtag="", max_results=200)


def test_search_hashtag_max_results_too_low():
    """Test with max_results < 10 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        SearchHashtagRequest(hashtag="#test", max_results=5)
    assert "Input should be greater than or equal to 10" in str(exc_info.value)


def test_search_hashtag_max_results_too_high():
    """Test with max_results > 100 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        SearchHashtagRequest(hashtag="#test", max_results=101)
    assert "Input should be less than or equal to 100" in str(exc_info.value)


def test_search_hashtag_max_results_zero():
    """Test with max_results = 0 (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        SearchHashtagRequest(hashtag="#test", max_results=0)
    assert "Input should be greater than or equal to 10" in str(exc_info.value)


def test_search_hashtag_max_results_negative():
    """Test with negative max_results (should fail)"""
    with pytest.raises(PydanticValidationError) as exc_info:
        SearchHashtagRequest(hashtag="#test", max_results=-1)
    assert "Input should be greater than or equal to 10" in str(exc_info.value)


# === Complex Integration Tests ===


def test_create_tweet_all_fields(common_test_data, schema_constants):
    """Test CreateTweetRequest with all fields populated"""
    model = CreateTweetRequest(
        text="This is a comprehensive tweet with all features!",
        image_content_str=common_test_data["base64_image"],
        poll_options=["Option 1", "Option 2", "Option 3"],
        poll_duration=1440,  # 24 hours
        in_reply_to_tweet_id=common_test_data["reply_tweet_id"],
        quote_tweet_id=common_test_data["quote_tweet_id"]
    )
    assert model.text == "This is a comprehensive tweet with all features!"
    assert model.image_content_str == common_test_data["base64_image"]
    assert model.poll_options == ["Option 1", "Option 2", "Option 3"]
    assert model.poll_duration == 1440
    assert model.in_reply_to_tweet_id == common_test_data["reply_tweet_id"]
    assert model.quote_tweet_id == common_test_data["quote_tweet_id"]


def test_create_tweet_edge_case_combinations(boundary_test_data):
    """Test edge case combinations for CreateTweetRequest"""
    # Maximum length text with minimum poll options and duration
    model = CreateTweetRequest(
        text=boundary_test_data["max_length_text"],
        poll_options=boundary_test_data["min_poll_data"]["options"],
        poll_duration=boundary_test_data["min_poll_data"]["duration"]
    )
    assert len(model.text) == 280
    assert len(model.poll_options) == 2
    assert model.poll_duration == 5


def test_create_tweet_boundary_values(schema_factories, boundary_test_data):
    """Test boundary values for CreateTweetRequest"""
    # Text exactly at boundary - using factory for convenience
    model = schema_factories["create_tweet"](text="X")  # Minimum length
    assert len(model.text) == 1
    
    # Poll duration at boundaries
    model_min = schema_factories["create_tweet"](
        text="Poll test",
        poll_options=boundary_test_data["min_poll_data"]["options"],
        poll_duration=boundary_test_data["min_poll_data"]["duration"]
    )
    assert model_min.poll_duration == 5
    
    model_max = schema_factories["create_tweet"](
        text="Poll test",
        poll_options=boundary_test_data["max_poll_data"]["options"],
        poll_duration=boundary_test_data["max_poll_data"]["duration"]
    )
    assert model_max.poll_duration == 10080
    assert len(model_max.poll_options) == 4


def test_all_schemas_type_validation():
    """Test type validation across all schemas"""
    # Test that non-string values are rejected where strings are expected
    with pytest.raises(PydanticValidationError):
        CreateTweetRequest(text=123)  # Should be string
    
    with pytest.raises(PydanticValidationError):
        FollowUserRequest(user_id=456)  # Should be string
    
    with pytest.raises(PydanticValidationError):
        RetweetTweetRequest(tweet_id=789)  # Should be string
    
    # Test that non-list values are rejected where lists are expected
    with pytest.raises(PydanticValidationError):
        GetUserTweetsRequest(user_ids="single_user")  # Should be list
    
    with pytest.raises(PydanticValidationError):
        GetTrendsRequest(countries="USA")  # Should be list


def test_optional_fields_none_values():
    """Test that optional fields can be explicitly set to None"""
    model = CreateTweetRequest(
        text="Test tweet",
        image_content_str=None,
        poll_options=None,
        poll_duration=None,
        in_reply_to_tweet_id=None,
        quote_tweet_id=None
    )
    assert model.image_content_str is None
    assert model.poll_options is None
    assert model.poll_duration is None
    assert model.in_reply_to_tweet_id is None
    assert model.quote_tweet_id is None


def test_schema_string_representations():
    """Test that schemas have proper string representations"""
    model = CreateTweetRequest(text="Test")
    assert isinstance(str(model), str)
    assert isinstance(repr(model), str)
    
    model2 = GetUserTweetsRequest(user_ids=["123"])
    assert isinstance(str(model2), str)
    assert isinstance(repr(model2), str)


# === Serialization/Deserialization Tests ===


def test_create_tweet_serialization():
    """Test CreateTweetRequest serialization and deserialization"""
    original = CreateTweetRequest(
        text="Test tweet",
        image_content_str="image_data",
        poll_options=["A", "B"],
        poll_duration=60
    )
    
    # Test model_dump
    data = original.model_dump()
    assert data["text"] == "Test tweet"
    assert data["image_content_str"] == "image_data"
    assert data["poll_options"] == ["A", "B"]
    assert data["poll_duration"] == 60
    
    # Test reconstruction from dict
    reconstructed = CreateTweetRequest(**data)
    assert reconstructed.text == original.text
    assert reconstructed.image_content_str == original.image_content_str
    assert reconstructed.poll_options == original.poll_options
    assert reconstructed.poll_duration == original.poll_duration


def test_get_user_tweets_serialization():
    """Test GetUserTweetsRequest serialization"""
    original = GetUserTweetsRequest(user_ids=["1", "2", "3"], max_results=25)
    
    data = original.model_dump()
    assert data["user_ids"] == ["1", "2", "3"]
    assert data["max_results"] == 25
    
    reconstructed = GetUserTweetsRequest(**data)
    assert reconstructed.user_ids == original.user_ids
    assert reconstructed.max_results == original.max_results


def test_follow_user_serialization():
    """Test FollowUserRequest serialization"""
    original = FollowUserRequest(user_id="test_user_123")
    
    data = original.model_dump()
    assert data["user_id"] == "test_user_123"
    
    reconstructed = FollowUserRequest(**data)
    assert reconstructed.user_id == original.user_id


def test_retweet_serialization():
    """Test RetweetTweetRequest serialization"""
    original = RetweetTweetRequest(tweet_id="tweet_456")
    
    data = original.model_dump()
    assert data["tweet_id"] == "tweet_456"
    
    reconstructed = RetweetTweetRequest(**data)
    assert reconstructed.tweet_id == original.tweet_id


def test_get_trends_serialization():
    """Test GetTrendsRequest serialization"""
    original = GetTrendsRequest(countries=["USA", "Canada"], max_trends=15)
    
    data = original.model_dump()
    assert data["countries"] == ["USA", "Canada"]
    assert data["max_trends"] == 15
    
    reconstructed = GetTrendsRequest(**data)
    assert reconstructed.countries == original.countries
    assert reconstructed.max_trends == original.max_trends


def test_search_hashtag_serialization():
    """Test SearchHashtagRequest serialization"""
    original = SearchHashtagRequest(hashtag="#python", max_results=75)
    
    data = original.model_dump()
    assert data["hashtag"] == "#python"
    assert data["max_results"] == 75
    
    reconstructed = SearchHashtagRequest(**data)
    assert reconstructed.hashtag == original.hashtag
    assert reconstructed.max_results == original.max_results


# === Model Validation Edge Cases ===


def test_create_tweet_unicode_text():
    """Test CreateTweetRequest with unicode characters"""
    unicode_text = "Hello 🌍! This is a test with émojis and spécial chars ñ"
    model = CreateTweetRequest(text=unicode_text)
    assert model.text == unicode_text


def test_create_tweet_numeric_strings():
    """Test CreateTweetRequest with numeric strings in optional fields"""
    model = CreateTweetRequest(
        text="Reply tweet",
        in_reply_to_tweet_id="123456789012345678",
        quote_tweet_id="987654321098765432"
    )
    assert model.in_reply_to_tweet_id == "123456789012345678"
    assert model.quote_tweet_id == "987654321098765432"


def test_list_fields_immutability():
    """Test that list fields maintain their values correctly"""
    user_ids = ["user1", "user2", "user3"]
    model = GetUserTweetsRequest(user_ids=user_ids)
    
    # Modifying original list shouldn't affect model
    user_ids.append("user4")
    assert len(model.user_ids) == 3
    assert "user4" not in model.user_ids


def test_poll_options_special_characters():
    """Test poll options with special characters"""
    model = CreateTweetRequest(
        text="Poll with special chars",
        poll_options=["Option #1", "Choice & More", "2nd Option", "Final!"],
        poll_duration=120
    )
    assert len(model.poll_options) == 4
    assert "Option #1" in model.poll_options
    assert "Choice & More" in model.poll_options
