from django import template
from urllib.parse import urlparse, parse_qs

register = template.Library()


@register.filter
def embed_video(url):
    """
    Convert YouTube/Vimeo URLs into embeddable URLs.
    """
    if not url:
        return ""

    parsed = urlparse(url)

    # YouTube short link
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://www.youtube.com/embed/{video_id}"

    # YouTube watch link
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    # Vimeo
    if "vimeo.com" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://player.vimeo.com/video/{video_id}"

    return url