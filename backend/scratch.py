import requests
import urllib.parse
def search(name):
    url = f"https://site.web.api.espn.com/apis/search/v2?query={urllib.parse.quote_plus(name)}&limit=5"
    r = requests.get(url)
    print("Search Status:", r.status_code)
    try:
        data = r.json()
        for res in data.get('results', []):
            if 'contents' in res:
                for item in res['contents']:
                    print("Found:", item.get('displayName'), "| Type:", item.get('type'))
    except Exception as e:
        print("err", e)

def team(abbrev):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{abbrev}/roster"
    r = requests.get(url)
    print("Team Status:", r.status_code)

search("Patrick Mahomes")
team("kc")
