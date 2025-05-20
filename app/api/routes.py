from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from ..services.search import SearchService, get_search_service


router = APIRouter()

@router.get("/search", response_class=PlainTextResponse)
async def search_text(
    q: str = Query(..., description="Text to search for"),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Search for text in files stored in dropbox cloud storage.
            
    Returns:
        str: A newline-separated list of file paths that match the search query
        
    Raises:
        HTTPException: If the search operation fails
    """
    try:
        response = await search_service.search_files(
            query=q
        )
        return "\n".join(response.full_paths)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    finally:
        await search_service.close()