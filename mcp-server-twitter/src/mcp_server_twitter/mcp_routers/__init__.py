from mcp_server_twitter.mcp_routers.create_tweet import router as create_tweet_router
from mcp_server_twitter.mcp_routers.get_user_tweets import router as get_user_tweets_router
from mcp_server_twitter.mcp_routers.follow_user import router as follow_user_router
from mcp_server_twitter.mcp_routers.retweet_tweet import router as retweet_tweet_router
from mcp_server_twitter.mcp_routers.get_trends import router as get_trends_router
from mcp_server_twitter.mcp_routers.search_hashtag import router as search_hashtag_router

routers = [
    create_tweet_router,
    get_user_tweets_router,
    follow_user_router,
    retweet_tweet_router,
    get_trends_router,
    search_hashtag_router,
]
