"""Fetch site analytics via Plausible API."""
from typing import List, Optional

import requests
from requests.exceptions import RequestException

from clients import ghost
from config import settings
from log import LOGGER


def fetch_top_visited_urls(time_period, limit=20) -> List[Optional[dict]]:
    """
    Fetch top visited URLs from Plausible.

    :param str time_period: Period of 12mo, 6mo, month, 30d, 7d, or day.
    :param int limit: Maximum number of results to be returned.

    :returns: Optional[List[dict]]
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.PLAUSIBLE_API_TOKEN}",
        }
        params = {
            "site_id": "hackersandslackers.com",
            "period": time_period,
            "property": "event:page",
            "limit": limit,
        }
        resp = requests.get(
            settings.PLAUSIBLE_BREAKDOWN_ENDPOINT,
            params=params,
            headers=headers,
        )
        if resp.status_code == 200:
            results_list = resp.json().get("results")
            ghost_pages = [f"/{page['slug']}/" for page in ghost.get_pages()]
            results_list = [
                result
                for result in results_list
                if "/tag" not in result["page"]
                and "/page" not in result["page"]
                and "/author" not in result["page"]
                and result["page"] not in ghost_pages
            ]
            return [
                enrich_url_with_post_data(result)
                for result in results_list
                if result is not None
            ]
        return []
    except RequestException as e:
        LOGGER.error(f"RequestException when fetching Plausible top URLs: {e}")
    except Exception as e:
        LOGGER.error(f"Unexpected Exception when fetching Plausible top URLs: {e}")


def enrich_url_with_post_data(page_result: dict) -> Optional[dict]:
    """
    Determine post slug from URL & fetch Ghost post title.

    :param dict page_result: Top visited URL result returned by Plausible.

    :returns: Optional[dict]
    """
    slug = page_result["page"].rstrip("/").lstrip("/").split("/")[-1]
    post = ghost.get_post_by_slug(slug)
    if post is not None:
        page_result["slug"] = slug
        page_result["title"] = post["title"]
        page_result["url"] = f"https://hackersandslackers.com{post['url']}"
        return page_result
    return None