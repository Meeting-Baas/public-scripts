from fastapi import APIRouter, HTTPException
from .models import ComparisonRequest, ComparisonResponse
from .comparator import OpenAPIComparator
import os

router = APIRouter()
comparator = OpenAPIComparator()

@router.post("/compare", response_model=ComparisonResponse)
async def compare_commits(request: ComparisonRequest):
    """Compare OpenAPI specs between two commits."""
    try:
        # Validate repository path
        if not os.path.exists(request.repo_path):
            raise HTTPException(status_code=400, detail="Repository path does not exist")
        
        # Use repo_name from request or default to directory name
        repo_name = request.repo_name or os.path.basename(request.repo_path)
        
        # Run comparison
        result = comparator.compare_commits(
            request.repo_path,
            request.old_commit,
            request.new_commit,
            repo_name
        )
        
        return ComparisonResponse(
            status="success",
            message="Comparison completed successfully",
            diff_file=f"updates/{result.repo_name}-{result.timestamp.strftime('%Y-%m-%d')}-open-api-diff.md"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 