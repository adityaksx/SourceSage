from urllib.parse import urlparse


def detect_source(url: str) -> str:
    """
    Detect the source type from a URL.

    Returns possible values:
        youtube_video
        youtube_playlist
        instagram_post
        instagram_reel
        instagram_profile
        github_repo
        github_profile
        web
        unknown
    """

    if not url or not isinstance(url, str):
        return "unknown"

    try:
        parsed = urlparse(url.strip())

        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        # ------------------------
        # YOUTUBE
        # ------------------------
        if "youtube.com" in domain or "youtu.be" in domain:

            if "playlist" in url:
                return "youtube_playlist"

            return "youtube_video"

        # ------------------------
        # INSTAGRAM
        # ------------------------
        if "instagram.com" in domain:

            if "/reel/" in path:
                return "instagram_reel"

            if "/p/" in path:
                return "instagram_post"

            return "instagram_profile"

        # ------------------------
        # GITHUB
        # ------------------------
        if "github.com" in domain:

            parts = [p for p in path.split("/") if p]

            if len(parts) >= 2:
                return "github_repo"

            return "github_profile"

        # ------------------------
        # DEFAULT
        # ------------------------
        return "web"

    except Exception:
        return "unknown"


# Optional CLI test
if __name__ == "__main__":

    test_urls = [
        "https://youtube.com/watch?v=abc",
        "https://youtu.be/xyz",
        "https://youtube.com/playlist?list=123",
        "https://instagram.com/p/abc",
        "https://instagram.com/reel/xyz",
        "https://github.com/openai/gpt",
        "https://github.com/openai",
        "https://example.com/article"
    ]

    for url in test_urls:
        print(url, "→", detect_source(url))