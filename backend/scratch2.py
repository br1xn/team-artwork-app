import requests
import urllib.parse
name = "Patrick Mahomes"
url = f"https://site.web.api.espn.com/apis/search/v2?query={urllib.parse.quote_plus(name)}&limit=5"
r = requests.get(url)
for res in r.json().get('results', []):
    for item in res.get('contents', []):
        print(item.get('displayName'), "| type:", item.get('type'))
