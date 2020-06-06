"""Replace <a> tags in Lynx posts with cards."""
import re
import json
from .scrape import scrape_links
from .doc import mobile_doc
from api.log import LOGGER


@LOGGER.catch
def format_lynx_posts(post):
    """Replace <a> tags in Lynx posts."""
    html = post.get('html')
    links = re.findall('<a href="(.*?)"', html)
    link_previews = [scrape_links(link) for link in links]
    mobile_doc['cards'] = link_previews
    for i, link in enumerate(link_previews):
        mobile_doc['sections'].append([10, i])
    return json.dumps(mobile_doc)