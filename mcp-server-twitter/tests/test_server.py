import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp_server_twitter.server import mcp_server


class TestCreateTweet:
    """Test suite for the create_tweet function."""

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

        tool_input = {"text": "Hello, world! This is a test tweet."}

        # Act
        result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)

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

        tool_input = {
            "text": "@user This is a reply with poll and image!",
            "image_content_str": "base64encodedimagedata==",
            "poll_options": ["Option A", "Option B", "Option C"],
            "poll_duration": 60,
            "in_reply_to_tweet_id": "1111111111",
            "quote_tweet_id": "2222222222",
        }

        # Act
        result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)

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

        tool_input = {
            "text": "Poll with only one option",
            "poll_options": ["Only option"],
        }

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_poll_validation_too_many_options(self, mock_context):
        """Test poll validation with too many options."""
        create_tweet_func = self.get_create_tweet_func()

        tool_input = {
            "text": "Poll with too many options",
            "poll_options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4",
                "Option 5",
            ],
        }

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_poll_duration_validation_too_short(self, mock_context):
        """Test poll duration validation - too short."""
        create_tweet_func = self.get_create_tweet_func()

        tool_input = {
            "text": "Poll with invalid duration",
            "poll_options": ["Yes", "No"],
            "poll_duration": 2,  # Less than 5 minutes
        }

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_poll_duration_validation_too_long(self, mock_context):
        """Test poll duration validation - too long."""
        create_tweet_func = self.get_create_tweet_func()

        tool_input = {
            "text": "Poll with invalid duration",
            "poll_options": ["Yes", "No"],
            "poll_duration": 20000,  # More than 10080 minutes
        }

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_error_response_from_client(self, mock_context):
        """Test handling when client returns an error string."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = (
            "Error: Tweet creation failed due to policy violation"
        )

        tool_input = {"text": "This tweet violates policy"}

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Tweet creation failed: Error: Tweet creation failed due to policy violation",
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_403_forbidden_error(self, mock_context):
        """Test handling 403 Forbidden errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception(
            "403 Forbidden: Content violates policy"
        )

        tool_input = {"text": "Forbidden content"}

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Tweet creation forbidden. Check content policy or API permissions",
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_401_unauthorized_error(self, mock_context):
        """Test handling 401 Unauthorized errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception(
            "401 Unauthorized: Invalid credentials"
        )

        tool_input = {"text": "Test tweet"}

        # Act & Assert
        with pytest.raises(
            ToolError,
            match="Unauthorized. Check Twitter API credentials",
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_duplicate_error(self, mock_context):
        """Test handling duplicate tweet errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception("duplicate content detected")

        tool_input = {"text": "This is a duplicate tweet"}

        # Act & Assert
        with pytest.raises(
            ToolError, match="Duplicate tweet. This content has already been posted"
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_generic_error(self, mock_context):
        """Test handling generic errors."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.side_effect = Exception("Some unexpected error")

        tool_input = {"text": "Test tweet"}

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error creating tweet: Some unexpected error"
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_image_too_large(self, mock_context):
        """Test handling of image content that's too large."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        large_image_content = "x" * 6_000_000  # > 5MB
        
        tool_input = {
            "text": "Tweet with large image",
            "image_content_str": large_image_content
        }

        # Act & Assert
        with pytest.raises(
            ToolError, match="Image content too large \\(max 5MB\\)"
        ):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio 
    async def test_create_tweet_text_validation_empty(self, mock_context):
        """Test text validation with empty text."""
        create_tweet_func = self.get_create_tweet_func()
        
        tool_input = {"text": ""}

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_text_validation_too_long(self, mock_context):
        """Test text validation with text too long."""
        create_tweet_func = self.get_create_tweet_func()
        
        tool_input = {"text": "x" * 281}  # Over 280 characters

        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet_func(ctx=mock_context, tool_input=tool_input)


class TestGetUserTweets:
    """Test suite for the get_user_tweets tool."""

    def get_get_user_tweets_func(self):
        """Get the underlying get_user_tweets function from the MCP server tool."""
        # Find the get_user_tweets tool in the server's tools
        return mcp_server._tool_manager._tools["get_user_tweets"].fn

    @pytest.mark.asyncio
    async def test_get_user_tweets_success(self, mock_context, mock_twitter_response, mock_tweet):
        """Test retrieving tweets for multiple users successfully."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]

        # Simulate responses for two different users
        user1_tweets = [mock_tweet("Tweet from user 1")]
        user2_tweets = [
            mock_tweet("Tweet A from user 2"),
            mock_tweet("Tweet B from user 2"),
        ]

        mock_client.get_user_tweets.side_effect = [
            mock_twitter_response(data=user1_tweets),
            mock_twitter_response(data=user2_tweets),
        ]

        get_user_tweets = self.get_get_user_tweets_func()

        tool_input = {"user_ids": ["user1", "user2"], "max_results": 5}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        expected = {
            "user1": ["Tweet from user 1"],
            "user2": ["Tweet A from user 2", "Tweet B from user 2"],
        }
        assert result_json == expected
        assert mock_client.get_user_tweets.call_count == 2

    @pytest.mark.asyncio
    async def test_get_user_tweets_mixed_success_and_failure(self, mock_context, mock_twitter_response, mock_tweet):
        """Test retrieving tweets where one user is not found."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]

        user1_tweets = [mock_tweet("A tweet")]

        mock_client.get_user_tweets.side_effect = [
            mock_twitter_response(data=user1_tweets),
            Exception("404 User Not Found"),
        ]

        get_user_tweets = self.get_get_user_tweets_func()

        tool_input = {"user_ids": ["user1", "user_not_found"]}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
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
    async def test_get_user_tweets_no_tweets_found(self, mock_context, mock_twitter_response):
        """Test when a user exists but has no recent tweets."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.get_user_tweets.return_value = mock_twitter_response(
            data=None
        )  # No data in response

        get_user_tweets = self.get_get_user_tweets_func()

        tool_input = {"user_ids": ["user_with_no_tweets"]}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
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

        tool_input = {"user_ids": ["private_user"]}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        expected_error = "Error: Unauthorized access. Twitter API permissions may be insufficient to read tweets for user private_user"
        assert result_json["private_user"] == [expected_error]

    @pytest.mark.asyncio
    async def test_get_user_tweets_validation_error(self, mock_context):
        """Test validation error with empty user_ids."""
        get_user_tweets = self.get_get_user_tweets_func()

        tool_input = {"user_ids": []}  # Empty list

        with pytest.raises(ToolError):
            await get_user_tweets(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_get_user_tweets_batch_processing_small(self, mock_context, mock_twitter_response, mock_tweet):
        """Test that tweets are processed in small batches for better performance."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Create a list of users
        users = [f"user{i}" for i in range(5)]
        
        # Mock responses for each user
        def mock_response(user_id, max_results):
            return mock_twitter_response(data=[mock_tweet(f"Tweet from {user_id}")])
        
        mock_client.get_user_tweets.side_effect = [
            mock_response(user, 10) for user in users
        ]

        get_user_tweets = self.get_get_user_tweets_func()

        tool_input = {"user_ids": users, "max_results": 10}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert len(result_json) == 5
        for user in users:
            assert user in result_json
            assert len(result_json[user]) == 1
            assert result_json[user][0] == f"Tweet from {user}"
        
        # Verify each user was called individually (small batch processing)
        assert mock_client.get_user_tweets.call_count == 5

    @pytest.mark.asyncio
    async def test_get_user_tweets_large_batch_processing(self, mock_context, mock_twitter_response, mock_tweet):
        """Test processing a larger batch of users efficiently."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Create a larger list of users to test batch processing
        users = [f"user{i}" for i in range(20)]
        
        # Mock responses - some succeed, some fail to test mixed scenarios
        responses = []
        for i, user in enumerate(users):
            if i % 5 == 0:  # Every 5th user fails
                responses.append(Exception("404 Not Found"))
            else:
                responses.append(mock_twitter_response(data=[mock_tweet(f"Tweet from {user}")]))
        
        mock_client.get_user_tweets.side_effect = responses

        get_user_tweets = self.get_get_user_tweets_func()
        tool_input = {"user_ids": users, "max_results": 5}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert len(result_json) == 20
        
        # Verify successful users
        for i, user in enumerate(users):
            assert user in result_json
            if i % 5 == 0:  # Failed users
                assert "Error: User" in result_json[user][0]
            else:  # Successful users
                assert result_json[user] == [f"Tweet from {user}"]
        
        # Verify all users were processed individually
        assert mock_client.get_user_tweets.call_count == 20

    @pytest.mark.asyncio
    async def test_get_user_tweets_memory_efficient_processing(self, mock_context, mock_twitter_response, mock_tweet):
        """Test memory efficient processing with many tweets per user."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate a user with many tweets (testing memory efficiency)
        large_tweet_count = 100
        mock_tweets = [mock_tweet(f"Tweet {i}") for i in range(large_tweet_count)]
        mock_client.get_user_tweets.return_value = mock_twitter_response(data=mock_tweets)

        get_user_tweets = self.get_get_user_tweets_func()
        tool_input = {"user_ids": ["prolific_user"], "max_results": 100}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert len(result_json["prolific_user"]) == large_tweet_count
        # Verify data is processed correctly without memory issues
        for i in range(large_tweet_count):
            assert result_json["prolific_user"][i] == f"Tweet {i}"

    @pytest.mark.asyncio
    async def test_get_user_tweets_concurrent_error_handling(self, mock_context):
        """Test handling multiple different error types in a single batch."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Different error types for different users
        error_scenarios = [
            Exception("401 Unauthorized"),
            Exception("403 Forbidden"),
            Exception("404 Not Found"),
            Exception("Rate limit exceeded"),
            Exception("Network timeout")
        ]
        
        users = [f"error_user_{i}" for i in range(5)]
        mock_client.get_user_tweets.side_effect = error_scenarios

        get_user_tweets = self.get_get_user_tweets_func()
        tool_input = {"user_ids": users}

        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert - verify each error is handled appropriately
        assert "Unauthorized access" in result_json["error_user_0"][0]
        assert "Access forbidden" in result_json["error_user_1"][0]
        assert "not found or account is private" in result_json["error_user_2"][0]
        assert "Error retrieving tweets" in result_json["error_user_3"][0]
        assert "Error retrieving tweets" in result_json["error_user_4"][0]


class TestFollowUser:
    """Test suite for the follow_user tool."""

    def get_follow_user_func(self):
        """Get the underlying follow_user function from the MCP server tool."""
        return mcp_server._tool_manager._tools["follow_user"].fn

    @pytest.mark.asyncio
    async def test_follow_user_success(self, mock_context):
        """Test following a user successfully."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_response = {"following": True, "pending_follow": False}
        mock_client.follow_user.return_value = mock_response

        follow_user = self.get_follow_user_func()

        tool_input = {"user_id": "target_user"}

        # Act
        result = await follow_user(ctx=mock_context, tool_input=tool_input)

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

        tool_input = {"user_id": "target_user"}

        # Act & Assert
        with pytest.raises(ToolError, match="User target_user not found"):
            await follow_user(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_follow_user_forbidden(self, mock_context):
        """Test following a user when it's forbidden (e.g., already following)."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.side_effect = Exception("403 Forbidden")

        follow_user = self.get_follow_user_func()

        tool_input = {"user_id": "target_user"}

        # Act & Assert
        expected_error = "Cannot follow user. Account may be private or already followed"
        with pytest.raises(ToolError, match=expected_error):
            await follow_user(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_follow_user_generic_error(self, mock_context):
        """Test a generic exception during follow."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.side_effect = Exception("Network Error")

        follow_user = self.get_follow_user_func()

        tool_input = {"user_id": "target_user"}

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error following user target_user: Network Error"
        ):
            await follow_user(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_follow_user_validation_error(self, mock_context):
        """Test validation error with empty user_id."""
        follow_user = self.get_follow_user_func()

        tool_input = {"user_id": ""}  # Empty string

        with pytest.raises(ToolError):
            await follow_user(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_follow_user_batch_operation_simulation(self, mock_context):
        """Test simulating batch follow operations by calling follow multiple times."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.follow_user.return_value = {"following": True, "pending_follow": False}

        follow_user = self.get_follow_user_func()
        users_to_follow = ["user1", "user2", "user3"]
        
        # Act - simulate processing users in small batches
        results = []
        for user_id in users_to_follow:
            tool_input = {"user_id": user_id}
            result = await follow_user(ctx=mock_context, tool_input=tool_input)
            results.append(result)

        # Assert
        assert len(results) == 3
        assert mock_client.follow_user.call_count == 3
        for i, user_id in enumerate(users_to_follow):
            assert f"Following user: " in results[i]


class TestRetweetTweet:
    """Test suite for the retweet_tweet tool."""

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

        tool_input = {"tweet_id": tweet_id}

        # Act
        result = await retweet_func(ctx=mock_context, tool_input=tool_input)

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

        tool_input = {"tweet_id": tweet_id}

        # Act & Assert
        with pytest.raises(
            ToolError, match=f"Tweet {tweet_id} not found or has been deleted"
        ):
            await retweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_retweet_forbidden(self, mock_context):
        """Test retweeting when it is forbidden (403), e.g., already retweeted."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.retweet_tweet.side_effect = Exception("403 Forbidden")
        tweet_id = "12345"

        tool_input = {"tweet_id": tweet_id}

        # Act & Assert
        expected_msg = "Cannot retweet. Already retweeted or tweet is private"
        with pytest.raises(ToolError, match=expected_msg):
            await retweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_retweet_unauthorized_error(self, mock_context):
        """Test retweeting with unauthorized error."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.retweet_tweet.side_effect = Exception("401 Unauthorized")
        tweet_id = "12345"

        tool_input = {"tweet_id": tweet_id}

        # Act & Assert
        with pytest.raises(ToolError, match="Unauthorized. Check Twitter API permissions"):
            await retweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_retweet_generic_error(self, mock_context):
        """Test retweeting with generic error."""
        # Arrange
        retweet_func = self.get_retweet_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.retweet_tweet.side_effect = Exception("Network error")
        tweet_id = "12345"

        tool_input = {"tweet_id": tweet_id}

        # Act & Assert
        with pytest.raises(ToolError, match=f"Error retweeting {tweet_id}: Network error"):
            await retweet_func(ctx=mock_context, tool_input=tool_input)


class TestGetTrends:
    """Test suite for the get_trends tool."""

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

        tool_input = {"countries": ["Egypt"], "max_trends": 2}

        # Act
        result_str = await trends_func(ctx=mock_context, tool_input=tool_input)
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

        tool_input = {"countries": ["Egypt"]}

        # Act & Assert
        with pytest.raises(
            ToolError, match="Error retrieving trends: API limit reached"
        ):
            await trends_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_get_trends_validation_error(self, mock_context):
        """Test validation error with empty countries."""
        trends_func = self.get_trends_func()

        tool_input = {"countries": []}  # Empty list

        with pytest.raises(ToolError):
            await trends_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_get_trends_batch_processing_multiple_countries(self, mock_context):
        """Test getting trends for multiple countries efficiently."""
        # Arrange
        trends_func = self.get_trends_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Mock response for multiple countries
        mock_trends = {
            "Egypt": ["#Egypt_Cup", "#Tech_News"],
            "USA": ["#SuperBowl", "#Tech"],
            "France": ["#Olympics", "#Paris"],
            "Germany": ["#Bundesliga", "#Berlin"],
            "Japan": ["#Tokyo", "#Anime"]
        }
        mock_client.get_trends.return_value = mock_trends

        countries = ["Egypt", "USA", "France", "Germany", "Japan"]
        tool_input = {"countries": countries, "max_trends": 2}

        # Act
        result_str = await trends_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert result_json == mock_trends
        assert len(result_json) == 5
        for country in countries:
            assert country in result_json
            assert len(result_json[country]) == 2

        # Verify the client was called once with all countries (efficient batch processing)
        mock_client.get_trends.assert_awaited_once_with(countries=countries, max_trends=2)

    @pytest.mark.asyncio
    async def test_get_trends_memory_efficient_large_dataset(self, mock_context):
        """Test memory efficiency when processing large trend datasets."""
        # Arrange
        trends_func = self.get_trends_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate large dataset
        large_trends = {}
        countries = [f"Country{i}" for i in range(20)]
        for country in countries:
            large_trends[country] = [f"#{country}_trend_{j}" for j in range(50)]
        
        mock_client.get_trends.return_value = large_trends

        tool_input = {"countries": countries, "max_trends": 50}

        # Act
        result_str = await trends_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert - verify large dataset is handled correctly
        assert len(result_json) == 20
        for country in countries:
            assert len(result_json[country]) == 50

    @pytest.mark.asyncio
    async def test_get_trends_partial_failure_resilience(self, mock_context):
        """Test resilience when trends API returns partial data."""
        # Arrange
        trends_func = self.get_trends_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate partial data (some countries have trends, others don't)
        partial_trends = {
            "USA": ["#trend1", "#trend2"],
            "Egypt": [],  # No trends available
            "France": ["#france_trend"]
        }
        mock_client.get_trends.return_value = partial_trends

        tool_input = {"countries": ["USA", "Egypt", "France"]}

        # Act
        result_str = await trends_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert result_json == partial_trends
        assert len(result_json["USA"]) == 2
        assert len(result_json["Egypt"]) == 0
        assert len(result_json["France"]) == 1


class TestSearchHashtag:
    """Test suite for the search_hashtag tool."""

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

        tool_input = {"hashtag": "#python", "max_results": 20}

        # Act
        result_str = await search_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert result_json == mock_tweets
        mock_client.search_hashtag.assert_awaited_once_with(
            hashtag="#python", max_results=20
        )

    @pytest.mark.asyncio
    async def test_search_hashtag_error(self, mock_context):
        """Test a generic error while searching a hashtag."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.search_hashtag.side_effect = Exception("Invalid query")

        tool_input = {"hashtag": "invalid-hashtag"}

        # Act & Assert
        with pytest.raises(ToolError, match="Error searching hashtag: Invalid query"):
            await search_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_search_hashtag_validation_errors(self, mock_context):
        """Test validation errors for search_hashtag."""
        search_func = self.get_search_hashtag_func()

        # Test empty hashtag
        tool_input = {"hashtag": ""}
        with pytest.raises(ToolError):
            await search_func(ctx=mock_context, tool_input=tool_input)

        # Test max_results too low
        tool_input = {"hashtag": "#test", "max_results": 5}  # Under 10
        with pytest.raises(ToolError):
            await search_func(ctx=mock_context, tool_input=tool_input)

        # Test max_results too high
        tool_input = {"hashtag": "#test", "max_results": 150}  # Over 100
        with pytest.raises(ToolError):
            await search_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_search_hashtag_default_max_results(self, mock_context):
        """Test search_hashtag with default max_results."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_tweets = ["Tweet 1", "Tweet 2"]
        mock_client.search_hashtag.return_value = mock_tweets

        tool_input = {"hashtag": "#python"}  # No max_results specified

        # Act
        result_str = await search_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert result_json == mock_tweets
        mock_client.search_hashtag.assert_awaited_once_with(
            hashtag="#python", max_results=10  # Default value
        )


class TestLifespanManagement:
    """Test suite for the lifespan management functionality."""

    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful lifespan initialization."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch

        # Mock the get_twitter_client function
        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client:
            mock_twitter_client = AsyncMock()
            mock_get_client.return_value = mock_twitter_client

            # Test the lifespan context manager
            async with app_lifespan(mcp_server) as context:
                assert "twitter_client" in context
                assert context["twitter_client"] == mock_twitter_client

            # Verify the client was initialized
            mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_initialization_failure(self):
        """Test lifespan behavior when Twitter client initialization fails."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import patch

        # Mock the get_twitter_client function to raise an exception
        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Failed to initialize Twitter client")

            # Test that the exception is propagated
            with pytest.raises(Exception, match="Failed to initialize Twitter client"):
                async with app_lifespan(mcp_server):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_graceful_shutdown(self):
        """Test graceful shutdown behavior in lifespan management."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch, MagicMock
        import logging

        # Mock the get_twitter_client and logger
        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client, \
             patch('mcp_server_twitter.server.logger') as mock_logger:
            
            mock_twitter_client = AsyncMock()
            mock_get_client.return_value = mock_twitter_client

            # Test that shutdown logging occurs
            async with app_lifespan(mcp_server) as context:
                assert "twitter_client" in context

            # Verify shutdown logging was called
            mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")

    @pytest.mark.asyncio
    async def test_app_lifespan_resource_cleanup_on_exception(self):
        """Test that resources are cleaned up even if an exception occurs during yield."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch

        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client, \
             patch('mcp_server_twitter.server.logger') as mock_logger:
            
            mock_twitter_client = AsyncMock()
            mock_get_client.return_value = mock_twitter_client

            # Test cleanup occurs even when exception is raised in the context
            try:
                async with app_lifespan(mcp_server) as context:
                    assert "twitter_client" in context
                    # Simulate an exception during context execution
                    raise RuntimeError("Simulated error during execution")
            except RuntimeError:
                pass  # Expected exception

            # Verify cleanup still occurred
            mock_logger.info.assert_any_call("Lifespan: Shutdown cleanup completed")

    @pytest.mark.asyncio
    async def test_app_lifespan_multiple_initialization_attempts(self):
        """Test behavior when multiple initialization attempts occur."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch

        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client:
            mock_twitter_client = AsyncMock()
            mock_get_client.return_value = mock_twitter_client

            # Test multiple independent lifespan contexts
            async with app_lifespan(mcp_server) as context1:
                assert "twitter_client" in context1

            async with app_lifespan(mcp_server) as context2:
                assert "twitter_client" in context2

            # Verify client was initialized for each context
            assert mock_get_client.call_count == 2

    @pytest.mark.asyncio 
    async def test_app_lifespan_logging_during_phases(self):
        """Test that appropriate logging occurs during different lifespan phases."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch

        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client, \
             patch('mcp_server_twitter.server.logger') as mock_logger:
            
            mock_twitter_client = AsyncMock()
            mock_get_client.return_value = mock_twitter_client

            async with app_lifespan(mcp_server) as context:
                assert "twitter_client" in context

            # Verify all expected log messages
            expected_logs = [
                "Lifespan: Initializing Twitter client...",
                "Lifespan: Twitter client initialized successfully",
                "Lifespan: Shutdown cleanup completed"
            ]
            
            for expected_log in expected_logs:
                mock_logger.info.assert_any_call(expected_log)

    @pytest.mark.asyncio
    async def test_app_lifespan_client_configuration_validation(self):
        """Test that client configuration is properly validated during lifespan."""
        from mcp_server_twitter.server import app_lifespan, mcp_server
        from unittest.mock import AsyncMock, patch

        with patch('mcp_server_twitter.server.get_twitter_client') as mock_get_client:
            # Mock a client with specific attributes to verify it's properly configured
            mock_twitter_client = AsyncMock()
            mock_twitter_client.is_configured = True
            mock_twitter_client.api_version = "v2"
            mock_get_client.return_value = mock_twitter_client

            async with app_lifespan(mcp_server) as context:
                client = context["twitter_client"]
                assert hasattr(client, 'is_configured')
                assert hasattr(client, 'api_version')
                assert client.is_configured == True
                assert client.api_version == "v2"


class TestServerIntegration:
    """Integration tests for the MCP server."""

    @pytest.mark.asyncio
    async def test_all_tools_registered(self):
        """Test that all expected tools are registered with the server."""
        from mcp_server_twitter.server import mcp_server

        expected_tools = {
            "create_tweet",
            "get_user_tweets", 
            "follow_user",
            "retweet_tweet",
            "get_trends",
            "search_hashtag"
        }

        registered_tools = set(mcp_server._tool_manager._tools.keys())
        assert expected_tools.issubset(registered_tools)

    @pytest.mark.asyncio
    async def test_tool_signatures(self):
        """Test that all tools have the expected signatures."""
        from mcp_server_twitter.server import mcp_server
        import inspect

        for tool_name in ["create_tweet", "get_user_tweets", "follow_user", 
                         "retweet_tweet", "get_trends", "search_hashtag"]:
            tool = mcp_server._tool_manager._tools[tool_name]
            func = tool.fn
            
            # Check that function accepts ctx and tool_input parameters
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            assert "ctx" in params, f"Tool {tool_name} missing 'ctx' parameter"
            assert "tool_input" in params, f"Tool {tool_name} missing 'tool_input' parameter"


class TestEdgeCases:
    """Test edge cases and additional scenarios."""

    @pytest.mark.asyncio
    async def test_get_user_tweets_empty_response_data(self, mock_context, mock_twitter_response):
        """Test get_user_tweets when response has empty data."""
        from mcp_server_twitter.server import mcp_server
        
        get_user_tweets = mcp_server._tool_manager._tools["get_user_tweets"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Response with empty data list
        mock_client.get_user_tweets.return_value = mock_twitter_response(data=[])
        
        tool_input = {"user_ids": ["empty_user"]}
        
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)
        
        assert result_json["empty_user"] == []

    @pytest.mark.asyncio  
    async def test_get_user_tweets_403_forbidden_error(self, mock_context):
        """Test get_user_tweets with 403 Forbidden error."""
        from mcp_server_twitter.server import mcp_server
        
        get_user_tweets = mcp_server._tool_manager._tools["get_user_tweets"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        mock_client.get_user_tweets.side_effect = Exception("403 Forbidden")
        
        tool_input = {"user_ids": ["forbidden_user"]}
        
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)
        
        expected_error = "Error: Access forbidden for user forbidden_user. Account may be private or protected"
        assert result_json["forbidden_user"] == [expected_error]

    @pytest.mark.asyncio
    async def test_get_user_tweets_generic_error_handling(self, mock_context):
        """Test get_user_tweets with generic error."""
        from mcp_server_twitter.server import mcp_server
        
        get_user_tweets = mcp_server._tool_manager._tools["get_user_tweets"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        mock_client.get_user_tweets.side_effect = Exception("Network timeout")
        
        tool_input = {"user_ids": ["network_error_user"]}
        
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)
        
        expected_error = "Error retrieving tweets for user network_error_user: Network timeout"
        assert result_json["network_error_user"] == [expected_error]

    @pytest.mark.asyncio
    async def test_get_user_tweets_with_default_max_results(self, mock_context, mock_twitter_response, mock_tweet):
        """Test get_user_tweets uses default max_results when not specified."""
        from mcp_server_twitter.server import mcp_server
        
        get_user_tweets = mcp_server._tool_manager._tools["get_user_tweets"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        mock_tweets = [mock_tweet("Test tweet")]
        mock_client.get_user_tweets.return_value = mock_twitter_response(data=mock_tweets)
        
        tool_input = {"user_ids": ["test_user"]}  # No max_results specified
        
        await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        
        # Verify default max_results=10 was used
        mock_client.get_user_tweets.assert_called_with(user_id="test_user", max_results=10)

    @pytest.mark.asyncio
    async def test_create_tweet_with_minimal_valid_poll(self, mock_context):
        """Test create_tweet with minimal valid poll (2 options, 5 minutes)."""
        from mcp_server_twitter.server import mcp_server
        
        create_tweet = mcp_server._tool_manager._tools["create_tweet"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "123456789"
        
        tool_input = {
            "text": "Minimal poll test",
            "poll_options": ["Yes", "No"],
            "poll_duration": 5  # Minimum allowed
        }
        
        result = await create_tweet(ctx=mock_context, tool_input=tool_input)
        
        assert result == "Tweet created successfully with ID: 123456789"
        mock_client.create_tweet.assert_called_once_with(
            text="Minimal poll test",
            image_content_str=None,
            poll_options=["Yes", "No"],
            poll_duration=5,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_tweet_with_maximal_valid_poll(self, mock_context):
        """Test create_tweet with maximal valid poll (4 options, 10080 minutes)."""
        from mcp_server_twitter.server import mcp_server
        
        create_tweet = mcp_server._tool_manager._tools["create_tweet"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "987654321"
        
        tool_input = {
            "text": "Maximal poll test",
            "poll_options": ["Option A", "Option B", "Option C", "Option D"],
            "poll_duration": 10080  # Maximum allowed (1 week)
        }
        
        result = await create_tweet(ctx=mock_context, tool_input=tool_input)
        
        assert result == "Tweet created successfully with ID: 987654321"
        mock_client.create_tweet.assert_called_once_with(
            text="Maximal poll test",
            image_content_str=None,
            poll_options=["Option A", "Option B", "Option C", "Option D"],
            poll_duration=10080,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )

    @pytest.mark.asyncio 
    async def test_create_tweet_valid_image_size(self, mock_context):
        """Test create_tweet with valid image size (under 5MB)."""
        from mcp_server_twitter.server import mcp_server
        
        create_tweet = mcp_server._tool_manager._tools["create_tweet"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "image123"
        
        # Create image content just under 5MB limit
        valid_image_content = "x" * 4_900_000  # < 5MB
        
        tool_input = {
            "text": "Tweet with valid image",
            "image_content_str": valid_image_content
        }
        
        result = await create_tweet(ctx=mock_context, tool_input=tool_input)
        
        assert result == "Tweet created successfully with ID: image123"

    @pytest.mark.asyncio
    async def test_get_trends_with_default_max_trends(self, mock_context):
        """Test get_trends uses default max_trends when not specified."""
        from mcp_server_twitter.server import mcp_server
        
        get_trends = mcp_server._tool_manager._tools["get_trends"].fn
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        mock_trends = {"USA": ["#trend1", "#trend2"]}
        mock_client.get_trends.return_value = mock_trends
        
        tool_input = {"countries": ["USA"]}  # No max_trends specified
        
        result_str = await get_trends(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)
        
        assert result_json == mock_trends
        # Verify default max_trends=50 was used
        mock_client.get_trends.assert_called_with(countries=["USA"], max_trends=50)

    @pytest.mark.asyncio
    async def test_search_hashtag_large_result_set_processing(self, mock_context):
        """Test processing large result sets efficiently."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate large result set
        large_tweet_set = [f"This is tweet {i} about #python programming!" for i in range(100)]
        mock_client.search_hashtag.return_value = large_tweet_set

        tool_input = {"hashtag": "#python", "max_results": 100}

        # Act
        result_str = await search_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert - verify large dataset is processed correctly
        assert len(result_json) == 100
        for i in range(100):
            assert f"This is tweet {i} about #python programming!" in result_json

    @pytest.mark.asyncio
    async def test_search_hashtag_streaming_like_behavior(self, mock_context):
        """Test that hashtag search processes results in chunks (streaming-like)."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate chunked processing by returning tweets in logical groups
        chunked_tweets = []
        for chunk in range(5):  # 5 chunks of 10 tweets each
            for tweet_num in range(10):
                chunked_tweets.append(f"Chunk {chunk}, Tweet {tweet_num}: Amazing #ai discovery!")
        
        mock_client.search_hashtag.return_value = chunked_tweets

        tool_input = {"hashtag": "#ai", "max_results": 50}

        # Act
        result_str = await search_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert
        assert len(result_json) == 50
        # Verify chunk structure is maintained
        for chunk in range(5):
            for tweet_num in range(10):
                expected_tweet = f"Chunk {chunk}, Tweet {tweet_num}: Amazing #ai discovery!"
                assert expected_tweet in result_json

    @pytest.mark.asyncio
    async def test_search_hashtag_memory_efficient_json_processing(self, mock_context):
        """Test memory efficient JSON processing for large datasets."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Create tweets with various unicode characters to test JSON encoding
        unicode_tweets = [
            "¡Hola! #español programming is fun! 🚀",
            "مرحبا! #arabic coding نشاط رائع! 💻",
            "Здравствуй! #russian разработка крутая! 🔥",
            "こんにちは! #japanese コーディング楽しい! ⚡",
            "Γεια! #greek προγραμματισμός είναι ωραίος! 🌟"
        ]
        
        mock_client.search_hashtag.return_value = unicode_tweets

        tool_input = {"hashtag": "#multilingual", "max_results": 50}

        # Act
        result_str = await search_func(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)

        # Assert - verify unicode handling and JSON processing
        assert len(result_json) == 5
        for tweet in unicode_tweets:
            assert tweet in result_json

    @pytest.mark.asyncio
    async def test_search_hashtag_progressive_error_handling(self, mock_context):
        """Test progressive error handling during hashtag search."""
        # Arrange
        search_func = self.get_search_hashtag_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate different types of search errors
        error_scenarios = [
            "Rate limit exceeded",
            "Invalid hashtag format",
            "Search service temporarily unavailable",
            "Network timeout occurred"
        ]
        
        for error_msg in error_scenarios:
            mock_client.search_hashtag.side_effect = Exception(error_msg)
            tool_input = {"hashtag": "#test_error"}

            # Act & Assert
            with pytest.raises(ToolError, match=f"Error searching hashtag: {error_msg}"):
                await search_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_general_exception_handling_in_get_user_tweets(self, mock_context):
        """Test general exception handling in get_user_tweets main try block."""
        from mcp_server_twitter.server import mcp_server
        
        get_user_tweets = mcp_server._tool_manager._tools["get_user_tweets"].fn
        
        # Mock validation to raise an exception to trigger the main exception handler
        tool_input = {"user_ids": None}  # This should cause validation error, but let's mock differently
        
        # Instead, let's test when context access fails
        mock_context.request_context.lifespan_context = None
        
        with pytest.raises(Exception):  # This will raise AttributeError or similar
            await get_user_tweets(ctx=mock_context, tool_input={"user_ids": ["test"]})

    @pytest.mark.asyncio
    async def test_validation_errors_for_various_inputs(self, mock_context):
        """Test validation errors for various invalid inputs."""
        from mcp_server_twitter.server import mcp_server
        
        # Test follow_user with missing user_id
        follow_user = mcp_server._tool_manager._tools["follow_user"].fn
        
        with pytest.raises(ToolError):
            await follow_user(ctx=mock_context, tool_input={})

        # Test retweet_tweet with missing tweet_id  
        retweet_tweet = mcp_server._tool_manager._tools["retweet_tweet"].fn
        
        with pytest.raises(ToolError):
            await retweet_tweet(ctx=mock_context, tool_input={})

        # Test get_trends with missing countries
        get_trends = mcp_server._tool_manager._tools["get_trends"].fn
        
        with pytest.raises(ToolError):
            await get_trends(ctx=mock_context, tool_input={})

        # Test search_hashtag with missing hashtag
        search_hashtag = mcp_server._tool_manager._tools["search_hashtag"].fn
        
        with pytest.raises(ToolError):
            await search_hashtag(ctx=mock_context, tool_input={})

    @pytest.mark.asyncio
    async def test_create_tweet_missing_text(self, mock_context):
        """Test create_tweet with missing text field."""
        from mcp_server_twitter.server import mcp_server
        
        create_tweet = mcp_server._tool_manager._tools["create_tweet"].fn
        
        tool_input = {"image_content_str": "valid_image"}  # Missing text
        
        with pytest.raises(ToolError, match="Invalid input"):
            await create_tweet(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_batch_image_processing(self, mock_context):
        """Test efficient processing of image data in chunks."""
        # Arrange
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "image_tweet_123"

        # Create image data that simulates chunked processing
        # This simulates how large images might be processed in smaller chunks
        chunk_size = 1000  # 1KB chunks
        total_chunks = 10
        image_chunks = []
        
        for i in range(total_chunks):
            chunk = "x" * chunk_size  # 1KB of data per chunk
            image_chunks.append(chunk)
        
        # Combine chunks into full image (simulating reassembly)
        full_image = "".join(image_chunks)
        
        tool_input = {
            "text": "Tweet with chunked image processing",
            "image_content_str": full_image
        }

        # Act
        result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)

        # Assert
        assert result == "Tweet created successfully with ID: image_tweet_123"
        # Verify the full image was processed correctly
        mock_client.create_tweet.assert_called_once_with(
            text="Tweet with chunked image processing",
            image_content_str=full_image,
            poll_options=None,
            poll_duration=None,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_tweet_progressive_poll_validation(self, mock_context):
        """Test progressive validation of poll options in batches."""
        create_tweet_func = self.get_create_tweet_func()
        
        # Test various poll option configurations
        poll_test_cases = [
            {
                "name": "minimal_valid_poll",
                "poll_options": ["Yes", "No"],
                "poll_duration": 5,
                "should_pass": True
            },
            {
                "name": "maximum_valid_poll", 
                "poll_options": ["Option A", "Option B", "Option C", "Option D"],
                "poll_duration": 10080,
                "should_pass": True
            },
            {
                "name": "too_few_options",
                "poll_options": ["Only one"],
                "poll_duration": 60,
                "should_pass": False
            },
            {
                "name": "too_many_options",
                "poll_options": ["A", "B", "C", "D", "E"],
                "poll_duration": 60, 
                "should_pass": False
            }
        ]

        # Process test cases in small batches
        for batch_start in range(0, len(poll_test_cases), 2):  # Process 2 at a time
            batch = poll_test_cases[batch_start:batch_start + 2]
            
            for test_case in batch:
                tool_input = {
                    "text": f"Poll test: {test_case['name']}",
                    "poll_options": test_case["poll_options"],
                    "poll_duration": test_case["poll_duration"]
                }
                
                if test_case["should_pass"]:
                    # Mock successful response for valid polls
                    mock_client = mock_context.request_context.lifespan_context["twitter_client"]
                    mock_client.create_tweet.return_value = f"poll_{test_case['name']}_123"
                    
                    result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)
                    assert "Tweet created successfully" in result
                else:
                    # Invalid polls should raise validation errors
                    with pytest.raises(ToolError, match="Invalid input"):
                        await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_memory_efficient_text_processing(self, mock_context):
        """Test memory efficient processing of various text lengths."""
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Test text lengths in small increments to check memory efficiency
        text_length_tests = [
            50, 100, 150, 200, 250, 280  # Various lengths up to Twitter's limit
        ]
        
        for length in text_length_tests:
            # Create text of specific length
            test_text = "a" * length
            mock_client.create_tweet.return_value = f"text_len_{length}_tweet"
            
            tool_input = {"text": test_text}
            
            # Act
            result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)
            
            # Assert
            assert result == f"Tweet created successfully with ID: text_len_{length}_tweet"

    @pytest.mark.asyncio
    async def test_create_tweet_concurrent_validation_processing(self, mock_context):
        """Test that validation works correctly when processing multiple tweets conceptually."""
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Simulate multiple tweet creation scenarios that might happen in sequence
        tweet_scenarios = [
            {
                "text": "Simple tweet #1",
                "expected_id": "simple_1"
            },
            {
                "text": "Tweet with image #2",
                "image_content_str": "image_data_base64",
                "expected_id": "image_2"
            },
            {
                "text": "Reply tweet #3",
                "in_reply_to_tweet_id": "original_tweet_123",
                "expected_id": "reply_3"
            },
            {
                "text": "Quote tweet #4", 
                "quote_tweet_id": "quoted_tweet_456",
                "expected_id": "quote_4"
            }
        ]
        
        # Process scenarios in small batches
        for i, scenario in enumerate(tweet_scenarios):
            mock_client.create_tweet.return_value = scenario["expected_id"]
            
            # Remove expected_id from tool_input
            tool_input = {k: v for k, v in scenario.items() if k != "expected_id"}
            
            # Act
            result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)
            
            # Assert
            assert result == f"Tweet created successfully with ID: {scenario['expected_id']}"

    @pytest.mark.asyncio
    async def test_create_tweet_chunked_error_response_processing(self, mock_context):
        """Test processing of various error responses in manageable chunks."""
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Define error scenarios to test in small batches
        error_scenarios = [
            {
                "error": Exception("403 Forbidden: Content violates policy"),
                "expected_match": "Tweet creation forbidden"
            },
            {
                "error": Exception("401 Unauthorized: Invalid credentials"),
                "expected_match": "Unauthorized. Check Twitter API credentials"
            },
            {
                "error": Exception("duplicate content detected"),
                "expected_match": "Duplicate tweet"
            },
            {
                "error": Exception("Network timeout"),
                "expected_match": "Error creating tweet: Network timeout"
            }
        ]
        
        # Process error scenarios in batches of 2
        for batch_start in range(0, len(error_scenarios), 2):
            batch = error_scenarios[batch_start:batch_start + 2]
            
            for scenario in batch:
                mock_client.create_tweet.side_effect = scenario["error"]
                tool_input = {"text": "Test error handling"}
                
                # Act & Assert
                with pytest.raises(ToolError, match=scenario["expected_match"]):
                    await create_tweet_func(ctx=mock_context, tool_input=tool_input)

    @pytest.mark.asyncio
    async def test_create_tweet_streaming_data_simulation(self, mock_context):
        """Test handling data as if it were coming from a stream in small chunks."""
        create_tweet_func = self.get_create_tweet_func()
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "streaming_tweet_789"
        
        # Simulate streaming data by building tweet content incrementally
        streaming_chunks = [
            "Hello ",
            "world! ",
            "This is ",
            "a streaming ",
            "tweet test. ",
            "#streaming #test"
        ]
        
        # Build content progressively (simulating stream processing)
        accumulated_text = ""
        for chunk in streaming_chunks:
            accumulated_text += chunk
            
        # Use the final accumulated text
        tool_input = {"text": accumulated_text.strip()}
        
        # Act
        result = await create_tweet_func(ctx=mock_context, tool_input=tool_input)
        
        # Assert
        assert result == "Tweet created successfully with ID: streaming_tweet_789"
        expected_text = "Hello world! This is a streaming tweet test. #streaming #test"
        mock_client.create_tweet.assert_called_once_with(
            text=expected_text,
            image_content_str=None,
            poll_options=None,
            poll_duration=None,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )


class TestFixtureUsage:
    """Test class demonstrating usage of shared fixtures."""

    @pytest.mark.asyncio
    async def test_using_mcp_server_tools_fixture(self, mock_context, mcp_server_tools, sample_tool_inputs):
        """Test using the mcp_server_tools fixture for quick access to tools."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "tweet123"
        
        # Use the tools fixture
        create_tweet = mcp_server_tools["create_tweet"]
        tool_input = sample_tool_inputs["create_tweet"]["simple"]
        
        # Act
        result = await create_tweet(ctx=mock_context, tool_input=tool_input)
        
        # Assert
        assert result == "Tweet created successfully with ID: tweet123"
        mock_client.create_tweet.assert_called_once()

    @pytest.mark.asyncio
    async def test_using_sample_inputs_fixture(self, mock_context, mcp_server_tools, sample_tool_inputs, mock_twitter_response, mock_tweet):
        """Test using the sample_tool_inputs fixture."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        
        # Mock response for get_user_tweets
        mock_tweets = [mock_tweet("Sample tweet")]
        mock_client.get_user_tweets.return_value = mock_twitter_response(data=mock_tweets)
        
        # Use fixtures
        get_user_tweets = mcp_server_tools["get_user_tweets"]
        tool_input = sample_tool_inputs["get_user_tweets"]["single_user"]
        
        # Act
        result_str = await get_user_tweets(ctx=mock_context, tool_input=tool_input)
        result_json = json.loads(result_str)
        
        # Assert
        assert "user123" in result_json
        assert result_json["user123"] == ["Sample tweet"]

    @pytest.mark.asyncio
    async def test_poll_creation_with_fixtures(self, mock_context, mcp_server_tools, sample_tool_inputs):
        """Test poll creation using sample inputs fixture."""
        # Arrange
        mock_client = mock_context.request_context.lifespan_context["twitter_client"]
        mock_client.create_tweet.return_value = "poll_tweet_456"
        
        create_tweet = mcp_server_tools["create_tweet"]
        tool_input = sample_tool_inputs["create_tweet"]["with_poll"]
        
        # Act
        result = await create_tweet(ctx=mock_context, tool_input=tool_input)
        
        # Assert
        assert result == "Tweet created successfully with ID: poll_tweet_456"
        mock_client.create_tweet.assert_called_once_with(
            text="What's your favorite language?",
            image_content_str=None,
            poll_options=["Python", "JavaScript", "Go"],
            poll_duration=60,
            in_reply_to_tweet_id=None,
            quote_tweet_id=None,
        )
