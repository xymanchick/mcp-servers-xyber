from typing import Annotated, List, Optional

from pydantic import BaseModel, Field


class CreateTweetInput(BaseModel):
    text: Annotated[
        str,
        Field(
            min_length=1,
            max_length=280,
            description="Text of the tweet (1–280 chars)",
        ),
    ]
    image_content_str: Optional[str] = Field(
        default=None, description="Base64-encoded image content (optional)"
    )
    poll_options: Optional[
        Annotated[
            List[str],
            Field(
                min_length=2,
                max_length=4,
                description="List of 2 to 4 poll options",
            ),
        ]
    ] = None
    poll_duration: Optional[int] = Field(
        default=None,
        ge=5,
        le=10080,
        description="Poll duration in minutes (5–10080)",
    )
    in_reply_to_tweet_id: Optional[str] = Field(
        default=None, description="Tweet ID to reply to"
    )
    quote_tweet_id: Optional[str] = Field(
        default=None, description="Tweet ID to quote"
    )


class GetUserTweetsInput(BaseModel):
    user_ids: Annotated[
        list[str], Field(min_length=1, description="List of Twitter user IDs")
    ]
    max_results: Optional[Annotated[int, Field(ge=1, le=100)]] = 10


class FollowUserInput(BaseModel):
    user_id: Annotated[
        str, Field(min_length=1, description="Twitter user ID to follow")
    ]


class RetweetTweetInput(BaseModel):
    tweet_id: Annotated[
        str, Field(min_length=1, description="Tweet ID to retweet")
    ]


class GetTrendsInput(BaseModel):
    countries: Annotated[
        list[str], Field(min_length=1, description="List of country names")
    ]
    max_trends: Annotated[
        int, Field(ge=1, le=50, description="Max trends per country (1–50)")
    ] = 50


class SearchHashtagInput(BaseModel):
    hashtag: Annotated[
        str,
        Field(
            min_length=1, description="Hashtag to search (with or without #)"
        ),
    ]
    max_results: Annotated[
        int,
        Field(
            ge=10,
            le=100,
            description="Max number of tweets to return (10–100)",
        ),
    ] = 10
