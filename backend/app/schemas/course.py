from pydantic import BaseModel, HttpUrl
from typing import List, Optional


class CourseURLRequest(BaseModel):
    url: HttpUrl


class CourseContent(BaseModel):
    title: str
    sections: List[str]
    topics: List[str]
    summary: str
    raw_html: Optional[str] = None
    screenshots: Optional[List[str]] = None


class KnowledgeBase(BaseModel):
    id: str
    courses: List[CourseContent]
    created_at: str


class BrowserSession(BaseModel):
    session_id: str
    dcv_url: str
    status: str
