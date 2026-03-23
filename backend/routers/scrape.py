from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.firecrawl_service import scrape_linkedin

router = APIRouter()


class ScrapeRequest(BaseModel):
    linkedin_url: str


class ScrapeResponse(BaseModel):
    success: bool
    name: str = ""
    degree: str = ""
    university: str = ""
    graduation_year: int = 0
    current_job: str = ""
    current_company: str = ""
    error: str = ""


@router.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_profile(req: ScrapeRequest):
    result = await scrape_linkedin(req.linkedin_url)
    if not result:
        return ScrapeResponse(
            success=False,
            error="scrape_failed",
        )
    # TODO: LinkedIn markdown structure varies wildly and scraping often fails.
    # This is a best-effort stub. Manual entry is the reliable primary path.
    markdown = result.get("markdown", "")
    return ScrapeResponse(
        success=True,
        name=_extract_field(markdown, "name"),
        degree=_extract_field(markdown, "degree"),
        university=_extract_field(markdown, "university"),
        graduation_year=0,
        current_job=_extract_field(markdown, "job"),
    )


def _extract_field(markdown: str, field: str) -> str:
    return ""
