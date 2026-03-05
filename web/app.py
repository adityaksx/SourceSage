from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import sys
sys.path.append("..")

from main import process_link

app = FastAPI()

templates = Jinja2Templates(directory="web/templates")


class URLRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
def process(data: URLRequest):

    result = process_link(data.url)

    return {"result": result}