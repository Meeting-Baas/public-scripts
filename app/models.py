from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ComparisonRequest(BaseModel):
    repo_path: str
    old_commit: str
    new_commit: str
    repo_name: Optional[str] = None

class ComparisonResponse(BaseModel):
    status: str
    message: str
    diff_file: Optional[str] = None
    timestamp: datetime = datetime.now()

class ComparisonResult(BaseModel):
    diff_content: str
    repo_name: str
    old_commit: str
    new_commit: str
    timestamp: datetime = datetime.now() 