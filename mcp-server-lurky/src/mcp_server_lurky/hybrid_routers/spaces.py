from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from mcp_server_lurky.dependencies import get_lurky_client, get_db
from mcp_server_lurky.lurky.module import LurkyClient
from mcp_server_lurky.schemas import SpaceDetailsSchema, SearchResponseSchema

router = APIRouter(tags=["Spaces"])


@router.get("/search", response_model=SearchResponseSchema, operation_id="lurky_search_spaces")
async def search_spaces(
    q: str = Query(..., description="Search term for spaces"),
    limit: int = Query(10, ge=1, le=20),
    page: int = Query(0, ge=0),
    client: LurkyClient = Depends(get_lurky_client)
):
    """Search for discussions based on a keyword."""
    try:
        results = await client.search_discussions(q, limit=limit, page=page)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spaces/{space_id}", response_model=SpaceDetailsSchema, operation_id="lurky_get_space_details")
async def get_space_details(
    space_id: str,
    client: LurkyClient = Depends(get_lurky_client),
    db = Depends(get_db)
):
    """Get full details and summary for a specific Space ID."""
    # Check cache
    cached = db.get_space(space_id)
    if cached:
        # Convert SQLAlchemy model to Pydantic
        # This is a bit simplified, ideally use a converter
        return SpaceDetailsSchema(
            id=cached.id,
            creator_id=cached.creator_id,
            creator_handle=cached.creator_handle,
            title=cached.title,
            summary=cached.summary,
            minimized_summary=cached.minimized_summary,
            state=cached.state,
            language=cached.language,
            overall_sentiment=cached.overall_sentiment,
            participant_count=cached.participant_count or 0,
            subscriber_count=cached.subscriber_count or 0,
            likes=cached.likes or 0,
            categories=cached.categories or [],
            created_at=int(cached.created_at.timestamp() * 1000) if cached.created_at else None,
            started_at=int(cached.started_at.timestamp() * 1000) if cached.started_at else None,
            scheduled_at=int(cached.scheduled_at.timestamp() * 1000) if cached.scheduled_at else None,
            ended_at=int(cached.ended_at.timestamp() * 1000) if cached.ended_at else None,
            analyzed_at=int(cached.analyzed_at.timestamp() * 1000) if cached.analyzed_at else None,
            discussions=[
                {
                    "id": d.id,
                    "space_id": d.space_id,
                    "title": d.title,
                    "summary": d.summary,
                    "timestamp": int(d.timestamp.timestamp() * 1000) if d.timestamp else None,
                    "coins": d.coins or [],
                    "categories": d.categories or []
                } for d in cached.discussions
            ]
        )

    try:
        details = await client.get_space_details(space_id)
        # Fetch discussions
        discussions = await client.get_space_discussions(space_id)
        details.discussions = discussions
        
        # Save to cache
        db.save_space(details.model_dump())
        
        return details
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Space {space_id} not found: {e}")


@router.get("/latest-summaries", response_model=List[SpaceDetailsSchema], operation_id="lurky_get_latest_summaries")
async def get_latest_summaries(
    topic: str = Query(..., description="Topic to fetch latest summaries for"),
    count: int = Query(3, ge=1, le=10),
    client: LurkyClient = Depends(get_lurky_client)
):
    """Fetch the latest N unique space summaries for a given topic."""
    try:
        summaries = await client.get_latest_summaries(topic, count=count)
        if not summaries:
            raise HTTPException(status_code=404, detail=f"No summaries found for topic: {topic}")
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
