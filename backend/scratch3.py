import requests
r = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/lal/roster')
data = r.json()
print(data['athletes'][0].keys() if len(data['athletes']) > 0 else "No athletes")
if len(data['athletes']) > 0:
    for item in data['athletes'][0].get("items", []):
        print(item.get("fullName"), item.get("headshot", {}).get("href") if item.get("headshot") else "NO IMAGE")
