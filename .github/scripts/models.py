from typing import List, Optional
from pydantic import BaseModel

class FileEntry(BaseModel):
    filename: str
    arch: str
    platform: str
    platform_version: Optional[str] = None
    download_url: str

class ManifestEntry(BaseModel):
    version: str
    stable: bool
    release_url: str
    files: List[FileEntry]

