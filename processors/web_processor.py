import trafilatura
import requests


def extract_content(url: str) -> str:
    """
    Extract main readable content from any webpage
    (articles, blogs, tutorials, news, course pages)
    """

    try:
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            return None

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_recall=True
        )

        return text

    except Exception as e:
        print("Web extraction error:", e)
        return None


def process_web(url: str):
    """
    Main processor for web content
    """

    content = extract_content(url)

    if not content:
        return None

    return {
        "content": content
    }