import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import Context
from fastmcp.exceptions import ToolError


from mcp_server_twitter.server import mcp_server


class TestCreateTweet:
    """Test suite for the create_tweet function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object with twitter_client."""
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_create_tweet_func(self):
        """Get the underlying create_tweet function from the MCP server tool."""
        # Find the create_tweet tool in the server's tools
        return mcp_server._tool_manager._tools["create_tweet"].fn

    @pytest.mark.asyncio
    async def test_create_tweet_success(self, mock_context):
        """Test successful tweet creation."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "1234567890"

        # Act
        result = await create_tweet_func(
            ctx=mock_context, text="Hello, world! This is a test tweet."
        )

        # Assert
        assert result == "Tweet created successfully with ID: 1234567890"
        mock_client.create_tweet.assert_called_once_with(
            text="Hello, world! This is a test tweet.",
            image_content_str=None,
            poll_options=None,
            poll_duration=None,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_tweet_with_all_parameters(self, mock_context):
        """Test tweet creation with all optional parameters."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "9876543210"

        # Act
        result = await create_tweet_func(
            ctx=mock_context,
            text="@user This is a reply with poll and image!",
            image_content_str="base64encodedimagedata==",
            poll_options=["Option A", "Option B", "Option C"],
            poll_duration=60,
            in_reply_to_tweet_id="1111111111",
            quote_tweet_id="2222222222",
        )

        # Assert
        assert result == "Tweet created successfully with ID: 9876543210"
        mock_client.create_tweet.assert_called_once_with(
            text="@user This is a reply with poll and image!",
            image_content_str="base64encodedimagedata==",
            poll_options=["Option A", "Option B", "Option C"],
            poll_duration=60,
            in_reply_to_tweet_id="1111111111",
            quote_tweet_id="2222222222",
        )

    @pytest.mark.asyncio
    async def test_create_tweet_poll_validation_too_few_options(self, mock_context):
        """Test poll validation with too few options."""
        create_tweet_func = self.get_create_tweet_func()

        with pytest.raises(ToolError, match="Poll must have 2-4 options"):
            await create_tweet_func(
                ctx=mock_context,
                text="Poll with only one option",
                poll_options=["Only option"],
            )

    @pytest.mark.asyncio
    async def test_create_tweet_poll_validation_too_many_options(self, mock_context):
        """Test poll validation with too many options."""
        create_tweet_func = self.get_create_tweet_func()

        with pytest.raises(ToolError, match="Poll must have 2-4 options"):
            await create_tweet_func(
                ctx=mock_context,
                text="Poll with too many options",
                poll_options=[
                    "Option 1",
                    "Option 2",
                    "Option 3",
                    "Option 4",
                    "Option 5",
                ],
            )

    @pytest.mark.asyncio
    async def test_create_tweet_poll_duration_validation_too_short(self, mock_context):
        """Test poll duration validation - too short."""
        create_tweet_func = self.get_create_tweet_func()

        with pytest.raises(ToolError, match="Poll duration must be 5-10080 minutes"):
            await create_tweet_func(
                ctx=mock_context,
                text="Poll with invalid duration",
                poll_options=["Yes", "No"],
                poll_duration=2,  # Less than 5 minutes
            )

    @pytest.mark.asyncio
    async def test_create_tweet_poll_duration_validation_too_long(self, mock_context):
        """Test poll duration validation - too long."""
        create_tweet_func = self.get_create_tweet_func()

        with pytest.raises(ToolError, match="Poll duration must be 5-10080 minutes"):
            await create_tweet_func(
                ctx=mock_context,
                text="Poll with invalid duration",
                poll_options=["Yes", "No"],
                poll_duration=20000,  # More than 10080 minutes
            )

    @pytest.mark.asyncio
    async def test_create_tweet_error_response_from_client(self, mock_context):
        """Test handling when client returns an error string."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = (
            "Error: Tweet creation failed due to policy violation"
        )

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Tweet creation failed: Error: Tweet creation failed due to policy violation",
        ):
            await create_tweet_func(ctx=mock_context, text="This tweet violates policy")

    @pytest.mark.asyncio
    async def test_create_tweet_403_forbidden_error(self, mock_context):
        """Test handling 403 Forbidden errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception(
            "403 Forbidden: Content violates policy"
        )

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Tweet creation forbidden. Check content policy or API permissions",
        ):
            await create_tweet_func(ctx=mock_context, text="Forbidden content")

    @pytest.mark.asyncio
    async def test_create_tweet_401_unauthorized_error(self, mock_context):
        """Test handling 401 Unauthorized errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception(
            "401 Unauthorized: Invalid credentials"
        )

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Unauthorized. Check Twitter API credentials and permissions",
        ):
            await create_tweet_func(ctx=mock_context, text="Test tweet")

    @pytest.mark.asyncio
    async def test_create_tweet_duplicate_error(self, mock_context):
        """Test handling duplicate tweet errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception("duplicate content detected")

        # Act & Assert
        with pytest.raises(
            ToolError, match="Duplicate tweet. This content has already been posted"
        ):
            await create_tweet_func(ctx=mock_context, text="This is a duplicate tweet")

    @pytest.mark.asyncio
    async def test_create_tweet_generic_error(self, mock_context):
        """Test handling generic errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception("Some unexpected error")

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error creating tweet: Some unexpected error"
        ):
            await create_tweet_func(ctx=mock_context, text="Test tweet")


class MockTwitterResponse:
    def __init__(self, data=None):
        self.data = data


# This mock class simulates a single tweet object
class MockTweet:
    def __init__(self, text):
        self.text = text


class TestGetUserTweets:
    """Test suite for the get_user_tweets tool."""

    @pytest.fixture
    def mock_context(self) -> Context:
        """Create a mock Context object with a mock twitter_client."""
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_get_user_tweets_func(self):
        """Get the underlying create_tweet function from the MCP server tool."""
        # Find the create_tweet tool in the server's tools
        return mcp_server._tool_manager._tools["get_user_tweets"].fn

    @pytest.mark.asyncio
    async def test_get_user_tweets_success(self, mock_context):
        """Test retrieving tweets for multiple users successfully."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]

        # Simulate responses for two different users
        user1_tweets = [MockTweet("Tweet from user 1")]
        user2_tweets = [
            MockTweet("Tweet A from user 2"),
            MockTweet("Tweet B from user 2"),
        ]

        mock_client.get_user_tweets.side_effect = [
            MockTwitterResponse(data=user1_tweets),
            MockTwitterResponse(data=user2_tweets),
        ]

        get_user_tweets = self.get_get_user_tweets_func()

        # Act
        result_str = await get_user_tweets(
            ctx=mock_context, user_ids=["user1", "user2"], max_results=5
        )
        result_json = json.loads(result_str)

        # Assert
        expected = {
            "user1": ["Tweet from user 1"],
            "user2": ["Tweet A from user 2", "Tweet B from user 2"],
        }
        assert result_json == expected
        assert mock_client.get_user_tweets.call_count == 2

    @pytest.mark.asyncio
    async def test_get_user_tweets_mixed_success_and_failure(self, mock_context):
        """Test retrieving tweets where one user is not found."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]

        user1_tweets = [MockTweet("A tweet")]

        mock_client.get_user_tweets.side_effect = [
            MockTwitterResponse(data=user1_tweets),
            Exception("404 User Not Found"),
        ]

        get_user_tweets = self.get_get_user_tweets_func()

        # Act
        result_str = await get_user_tweets(
            ctx=mock_context, user_ids=["user1", "user_not_found"]
        )
        result_json = json.loads(result_str)

        # Assert
        expected = {
            "user1": ["A tweet"],
            "user_not_found": [
                "Error: User user_not_found not found or account is private/suspended"
            ],
        }
        assert result_json == expected

    @pytest.mark.asyncio
    async def test_get_user_tweets_no_tweets_found(self, mock_context):
        """Test when a user exists but has no recent tweets."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.get_user_tweets.return_value = MockTwitterResponse(
            data=None
        )  # No data in response

        get_user_tweets = self.get_get_user_tweets_func()

        # Act
        result_str = await get_user_tweets(
            ctx=mock_context, user_ids=["user_with_no_tweets"]
        )
        result_json = json.loads(result_str)

        # Assert
        assert result_json["user_with_no_tweets"] == []

    @pytest.mark.asyncio
    async def test_get_user_tweets_unauthorized_error(self, mock_context):
        """Test handling of a 401 Unauthorized error for a user."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.get_user_tweets.side_effect = Exception("401 Unauthorized")

        get_user_tweets = self.get_get_user_tweets_func()

        # Act
        result_str = await get_user_tweets(ctx=mock_context, user_ids=["private_user"])
        result_json = json.loads(result_str)

        # Assert
        expected_error = "Error: Unauthorized access. Twitter API permissions may be insufficient to read tweets for user private_user"
        assert result_json["private_user"] == [expected_error]


class TestFollowUser:
    """Test suite for the follow_user tool."""

    @pytest.fixture
    def mock_context(self) -> Context:
        """Create a mock Context object with a mock twitter_client."""
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_follow_user_func(self):
        """Get the underlying create_tweet function from the MCP server tool."""
        # Find the create_tweet tool in the server's tools
        return mcp_server._tool_manager._tools["follow_user"].fn

    @pytest.mark.asyncio
    async def test_follow_user_success(self, mock_context):
        """Test following a user successfully."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_response = {"following": True, "pending_follow": False}
        mock_client.follow_user.return_value = mock_response

        follow_user = self.get_follow_user_func()

        # Act
        result = await follow_user(ctx=mock_context, user_id="target_user")

        # Assert
        assert result == f"Following user: {mock_response}"
        mock_client.follow_user.assert_awaited_once_with("target_user")

    @pytest.mark.asyncio
    async def test_follow_user_not_found(self, mock_context):
        """Test following a user that does not exist."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.side_effect = Exception("404 Not Found")

        follow_user = self.get_follow_user_func()

        # Act & Assert
        with pytest.raises(ToolError, match="User target_user not found"):
            await follow_user(ctx=mock_context, user_id="target_user")

    @pytest.mark.asyncio
    async def test_follow_user_forbidden(self, mock_context):
        """Test following a user when it's forbidden (e.g., already following)."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.side_effect = Exception("403 Forbidden")

        follow_user = self.get_follow_user_func()

        # Act & Assert
        expected_error = "Cannot follow user target_user. Account may be private or you may already be following them"
        with pytest.raises(ToolError, match=expected_error):
            await follow_user(ctx=mock_context, user_id="target_user")

    @pytest.mark.asyncio
    async def test_follow_user_generic_error(self, mock_context):
        """Test a generic exception during follow."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.side_effect = Exception("Network Error")

        follow_user = self.get_follow_user_func()

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error following user target_user: Network Error"
        ):
            await follow_user(ctx=mock_context, user_id="target_user")


class TestRetweetTweet:
    """Test suite for the retweet_tweet tool."""

    @pytest.fixture
    def mock_context(self) -> Context:
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_retweet_tweet_func(self):
        """Get the underlying retweet_tweet function from the MCP server tool."""
        return mcp_server._tool_manager._tools["retweet_tweet"].fn

    @pytest.mark.asyncio
    async def test_retweet_success(self, mock_context):
        """Test a successful retweet."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_response = {"data": {"retweeted": True}}
        mock_client.retweet_tweet.return_value = mock_response
        tweet_id = "12345"

        # Act
        result = await retweet_func(ctx=mock_context, tweet_id=tweet_id)

        # Assert
        assert result == f"Retweeting tweet: {mock_response}"
        mock_client.retweet_tweet.assert_awaited_once_with(tweet_id)

    @pytest.mark.asyncio
    async def test_retweet_not_found(self, mock_context):
        """Test retweeting a tweet that is not found (404)."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.retweet_tweet.side_effect = Exception("404 Not Found")
        tweet_id = "12345"

        # Act & Assert
        with pytest.raises(
            ToolError, match=f"Tweet {tweet_id} not found or has been deleted"
        ):
            await retweet_func(ctx=mock_context, tweet_id=tweet_id)

    @pytest.mark.asyncio
    async def test_retweet_forbidden(self, mock_context):
        """Test retweeting when it is forbidden (403), e.g., already retweeted."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.retweet_tweet.side_effect = Exception("403 Forbidden")
        tweet_id = "12345"

        # Act & Assert
        expected_msg = f"Cannot retweet {tweet_id}. Tweet may be private or you may have already retweeted it"
        with pytest.raises(ToolError, match=expected_msg):
            await retweet_func(ctx=mock_context, tweet_id=tweet_id)


class TestGetTrends:
    """Test suite for the get_trends tool."""

    @pytest.fixture
    def mock_context(self) -> Context:
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_trends_func(self):
        """Get the underlying get_trends function from the MCP server tool."""
        return mcp_server._tool_manager._tools["get_trends"].fn

    @pytest.mark.asyncio
    async def test_get_trends_success(self, mock_context):
        """Test getting trends successfully."""
        # Arrange
        trends_func = self.get_trends_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_trends = {"Egypt": ["#Egypt_Cup", "#Tech_News"]}
        mock_client.get_trends.return_value = mock_trends

        # Act
        result_str = await trends_func(
            ctx=mock_context, countries=["Egypt"], max_trends=2
        )
        result_json = json.loads(result_str)

        # Assert
        assert result_json == mock_trends
        mock_client.get_trends.assert_awaited_once_with(
            countries=["Egypt"], max_trends=2
        )

    @pytest.mark.asyncio
    async def test_get_trends_error(self, mock_context):
        """Test a generic error while getting trends."""
        # Arrange
        trends_func = self.get_trends_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.get_trends.side_effect = Exception("API limit reached")

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error retrieving trends: API limit reached"
        ):
            await trends_func(ctx=mock_context, countries=["Egypt"])


class TestSearchHashtag:
    """Test suite for the search_hashtag tool."""

    @pytest.fixture
    def mock_context(self) -> Context:
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {"twitter_client": AsyncMock()}
        return ctx

    def get_search_hashtag_func(self):
        """Get the underlying search_hashtag function from the MCP server tool."""
        return mcp_server._tool_manager._tools["search_hashtag"].fn

    @pytest.mark.asyncio
    async def test_search_hashtag_success(self, mock_context):
        """Test searching a hashtag successfully."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_tweets = [
            "This is a great tweet about #python!",
            "I love #python programming.",
        ]
        mock_client.search_hashtag.return_value = mock_tweets

        # Act
        result_str = await search_func(
            ctx=mock_context, hashtag="#python", max_results=2
        )
        result_json = json.loads(result_str)

        # Assert
        assert result_json == mock_tweets
        mock_client.search_hashtag.assert_awaited_once_with(
            hashtag="#python", max_results=2
        )

    @pytest.mark.asyncio
    async def test_search_hashtag_error(self, mock_context):
        """Test a generic error while searching a hashtag."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.search_hashtag.side_effect = Exception("Invalid query")

        # Act & Assert
        with pytest.raises(ToolError, match="Error searching hashtag: Invalid query"):
            await search_func(ctx=mock_context, hashtag="invalid-hashtag")
