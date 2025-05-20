from typing import List, Dict, Any
from pydantic import BaseModel, Field

class BaseSearchResponse(BaseModel):
    """
    Response from search class.
    """
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_hits: int = Field()


class Full_path_SearchResponse(BaseSearchResponse):
    """
    custom search response - full paths of files.
    """
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_hits: int = Field()

    @property
    def full_paths(self) -> List[str]:
        """
        Return the full paths of the results.
        """
        return [result["full_path"] for result in self.results]