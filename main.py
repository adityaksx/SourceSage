from utils.source_detector import detect_source
from utils.cleaner import clean_processor_output
from llm.prompt_builder import build_summary_prompt
from llm.summarizer import summarize

from processors.youtube_processor import process_youtube
from processors.github_processor import process_github
from processors.web_processor import process_web
from processors.instagram_processor import process_instagram

from database.db import save_resource, init_db


def process_link(url):

    source = detect_source(url)

    raw_data = None
    cleaned_data = None
    llm_output = None

    try:

        # -------------------------
        # PROCESS SOURCE
        # -------------------------

        if source.startswith("youtube"):
            raw_data = process_youtube(url)

        elif source.startswith("instagram"):
            raw_data = process_instagram(url)

        elif source.startswith("github"):
            raw_data = process_github(url)

        elif source == "web":
            raw_data = process_web(url)

        else:
            print("Unsupported source")
            return


        # -------------------------
        # CLEAN DATA
        # -------------------------

        cleaned_data = clean_processor_output(raw_data)


        # -------------------------
        # BUILD PROMPT
        # -------------------------

        prompt = build_summary_prompt(cleaned_data)


        # -------------------------
        # SUMMARIZE
        # -------------------------

        llm_output = summarize(prompt)


        return llm_output


        # -------------------------
        # SAVE TO DATABASE
        # -------------------------

        save_resource(
            source=source,
            url=url,
            title=raw_data.get("title"),
            raw_input={"url": url},
            raw_data=raw_data,
            cleaned_data=cleaned_data,
            llm_output=llm_output
        )


    except Exception as e:

        save_resource(
            source=source,
            url=url,
            raw_input={"url": url},
            status="error",
            error=str(e)
        )

        return f"Error: {str(e)}"


# -------------------------
# CLI ENTRY
# -------------------------

if __name__ == "__main__":

    init_db()

    while True:

        url = input("\nEnter resource link (or 'exit'): ")

        if url.lower() == "exit":
            break

        result = process_link(url)
        print(result)