# Gazzette API
> Gazzette API with scraped data from [Gazzette](https://www.gazette.gov.mv/)

## Installation and Deployment
*Development*

if you don't have uv, get it [here](https://github.com/astral-sh/uv).
```bash
git clone https://github.com/i701/gazzette-api.git
cd gazzette-api
uv venv
source venv/bin/activate
uv pip install -r requirements.txt
fastapi dev main.py
```


*Using docker compose*
```bash
docker compose up -d
```


## Credits, and Thanks to
* [Kudanai](https://github.com/kudanai) for his repository [Gazettegram
](https://github.com/kudanai/gazettegram)
