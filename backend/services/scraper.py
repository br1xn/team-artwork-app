from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from models.schemas import LogoSource, Player, PlayerCollectionResponse


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


@dataclass
class TeamAssetScraper:
    timeout: int = 10

    def find_logo_sources(self, team_name: str) -> list[LogoSource]:
        from services.logo_validator import LogoValidator

        return LogoValidator(timeout=self.timeout).fetch_candidate_logos(team_name)


@dataclass
class PlayerScraper:
    timeout: int = 10

    IPL_TEAMS = {
        "csk": "chennai-super-kings",
        "chennai super kings": "chennai-super-kings",
        "mi": "mumbai-indians",
        "mumbai indians": "mumbai-indians",
        "rcb": "royal-challengers-bengaluru",
        "royal challengers bengaluru": "royal-challengers-bengaluru",
        "royal challengers bangalore": "royal-challengers-bengaluru",
        "kkr": "kolkata-knight-riders",
        "kolkata knight riders": "kolkata-knight-riders",
        "srh": "sunrisers-hyderabad",
        "sunrisers hyderabad": "sunrisers-hyderabad",
        "rr": "rajasthan-royals",
        "rajasthan royals": "rajasthan-royals",
        "dc": "delhi-capitals",
        "delhi capitals": "delhi-capitals",
        "pbks": "punjab-kings",
        "punjab kings": "punjab-kings",
        "gt": "gujarat-titans",
        "gujarat titans": "gujarat-titans",
        "lsg": "lucknow-super-giants",
        "lucknow super giants": "lucknow-super-giants",
    }

    NFL_TEAMS = {
        "arizona cardinals": "ari",
        "atlanta falcons": "atl",
        "baltimore ravens": "bal",
        "buffalo bills": "buf",
        "carolina panthers": "car",
        "chicago bears": "chi",
        "cincinnati bengals": "cin",
        "cleveland browns": "cle",
        "dallas cowboys": "dal",
        "denver broncos": "den",
        "detroit lions": "det",
        "green bay packers": "gb",
        "houston texans": "hou",
        "indianapolis colts": "ind",
        "jacksonville jaguars": "jax",
        "kansas city chiefs": "kc",
        "chiefs": "kc",
        "las vegas raiders": "lv",
        "los angeles chargers": "lac",
        "los angeles rams": "lar",
        "miami dolphins": "mia",
        "minnesota vikings": "min",
        "new england patriots": "ne",
        "new orleans saints": "no",
        "new york giants": "nyg",
        "new york jets": "nyj",
        "philadelphia eagles": "phi",
        "pittsburgh steelers": "pit",
        "san francisco 49ers": "sf",
        "seattle seahawks": "sea",
        "tampa bay buccaneers": "tb",
        "tennessee titans": "ten",
        "washington commanders": "wsh",
    }

    NBA_TEAMS = {
        "atlanta hawks": "atl", "boston celtics": "bos", "brooklyn nets": "bkn",
        "charlotte hornets": "cha", "chicago bulls": "chi", "cleveland cavaliers": "cle",
        "dallas mavericks": "dal", "denver nuggets": "den", "detroit pistons": "det",
        "golden state warriors": "gs", "houston rockets": "hou", "indiana pacers": "ind",
        "los angeles clippers": "lac", "la clippers": "lac", "los angeles lakers": "lal",
        "lakers": "lal", "memphis grizzlies": "mem", "miami heat": "mia",
        "milwaukee bucks": "mil", "minnesota timberwolves": "min", "new orleans pelicans": "no",
        "new york knicks": "ny", "knicks": "ny", "oklahoma city thunder": "okc",
        "orlando magic": "orl", "philadelphia 76ers": "phi", "76ers": "phi",
        "phoenix suns": "pho", "portland trail blazers": "por", "sacramento kings": "sac",
        "san antonio spurs": "sa", "toronto raptors": "tor", "utah jazz": "utah",
        "washington wizards": "was",
    }

    def scrape_players(self, team_name: str) -> PlayerCollectionResponse:
        players = self._scrape_ipl_roster(team_name)
        if not players:
            players = self._scrape_nfl_roster(team_name)
        if not players:
            players = self._scrape_nba_roster(team_name)
        if not players:
            players = self._scrape_wikipedia_roster(team_name)
        if not players:
            players = self._scrape_espn_roster(team_name)
        players = self._clean_players(players)
        
        if not players:
            players = self._fallback_players()
        return PlayerCollectionResponse(team_name=team_name, players=players)

    def search_player_by_name(self, name: str) -> Player | None:
        url = f"https://site.web.api.espn.com/apis/search/v2?query={quote_plus(name)}&limit=5"
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            if response.status_code == 200:
                results = response.json().get('results', [])
                for res in results:
                    if 'contents' in res:
                        for item in res['contents']:
                            item_name = item.get('displayName', '')
                            
                            # Ensure it's actually an athlete
                            if item.get('type') not in ['athlete', 'player']:
                                continue
                                
                            if name.lower() in item_name.lower() or item_name.lower() in name.lower():
                                img = item.get('image', {}).get('default')
                                
                                # SAFELY EXTRACT POSITION (Handles strings or dicts depending on ESPN's mood)
                                pos_obj = item.get('position')
                                pos = ""
                                if isinstance(pos_obj, dict):
                                    pos = pos_obj.get('displayName') or pos_obj.get('abbreviation') or ""
                                elif isinstance(pos_obj, str):
                                    pos = pos_obj

                                # SAFELY EXTRACT TEAM (Handles strings or dicts)
                                team_obj = item.get('team')
                                team = ""
                                if isinstance(team_obj, dict):
                                    team = team_obj.get('displayName') or team_obj.get('abbreviation') or ""
                                elif isinstance(team_obj, str):
                                    team = team_obj

                                # BUILD CLEAN ROLE STRING
                                role_parts = [p for p in [pos, team] if p]
                                role = " - ".join(role_parts) if role_parts else "Active Roster"
                                
                                return Player(name=item_name, role=role, image_url=img, source="Verified Roster")
        except Exception as e:
            print(f"Player search error: {e}")
            pass
        return None

    def _scrape_ipl_roster(self, team_name: str) -> list[Player]:
        slug = self._ipl_slug(team_name)
        if not slug:
            return []

        url = f"https://www.iplt20.com/teams/{slug}"
        soup = self._get_soup(url)
        if not soup:
            return []

        players: list[Player] = []
        for card in soup.select(".ih-p-img"):
            name_node = card.select_one(".ih-p-name")
            role_node = card.select_one("span")
            image_node = card.select_one("img")
            name = self._clean_text(name_node.get_text(" ", strip=True)) if name_node else ""
            role = self._clean_text(role_node.get_text(" ", strip=True)) if role_node else None
            image_url = None
            if image_node:
                image_url = image_node.get("data-src") or image_node.get("src")
                image_url = urljoin(url, image_url) if image_url else None
            if not name or not self._looks_like_player_name(name):
                continue
            
            # Trust the scraped URL to avoid blocking and speed up processing
            players.append(Player(name=name, role=role, image_url=image_url, source="Verified Roster"))
        return players

    def _nfl_slug(self, team_name: str) -> str | None:
        lowered = self._clean_text(team_name).lower()
        if lowered in self.NFL_TEAMS:
            return self.NFL_TEAMS[lowered]
        for name, slug in self.NFL_TEAMS.items():
            if name in lowered or lowered in name:
                return slug
        return None

    def _scrape_nfl_roster(self, team_name: str) -> list[Player]:
        abbrev = self._nfl_slug(team_name)
        if not abbrev:
            return []

        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{abbrev}/roster"
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return []

        players: list[Player] = []
        for group in data.get("athletes", []):
            for item in group.get("items", []):
                name = item.get("fullName")
                role = item.get("position", {}).get("displayName")
                image_url = item.get("headshot", {}).get("href")
                
                if not name or not self._looks_like_player_name(name):
                    continue
                
                players.append(Player(name=name, role=role, image_url=image_url, source="Verified Roster"))
        return players

    def _nba_slug(self, team_name: str) -> str | None:
        lowered = self._clean_text(team_name).lower()
        if lowered in self.NBA_TEAMS:
            return self.NBA_TEAMS[lowered]
        for name, slug in self.NBA_TEAMS.items():
            if name in lowered or lowered in name:
                return slug
        return None

    def _scrape_nba_roster(self, team_name: str) -> list[Player]:
        abbrev = self._nba_slug(team_name)
        if not abbrev:
            return []

        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{abbrev}/roster"
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return []

        players: list[Player] = []
        for group in data.get("athletes", []):
            for item in group.get("items", []):
                name = item.get("fullName")
                role = item.get("position", {}).get("displayName")
                image_url = item.get("headshot", {}).get("href")
                
                if not name or not self._looks_like_player_name(name):
                    continue
                
                players.append(Player(name=name, role=role, image_url=image_url, source="Verified Roster"))
        return players

    def _scrape_wikipedia_roster(self, team_name: str) -> list[Player]:
        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(team_name.replace(' ', '_'))}"
        soup = self._get_soup(page_url)
        if not soup:
            return []

        current_roster = self._scrape_current_roster_section(soup)
        if current_roster:
            return current_roster

        players: list[Player] = []
        for table in soup.select("table.wikitable"):
            headers = [header.get_text(" ", strip=True).lower() for header in table.select("th")]
            if not any("player" in header or "name" in header for header in headers):
                continue
            for row in table.select("tr")[1:]:
                cells = row.select("td, th")
                if len(cells) < 2:
                    continue
                values = [self._clean_text(cell.get_text(" ", strip=True)) for cell in cells]
                name = self._first_likely_name(values)
                if not name:
                    continue
                role = self._first_role(values)
                image_url = self._extract_image_url(row, page_url)
                if image_url and not self._is_reachable_image(image_url):
                    image_url = None
                players.append(Player(name=name, role=role, image_url=image_url, source="Verified Roster"))
            if players:
                break
        return players

    def _scrape_current_roster_section(self, soup: BeautifulSoup) -> list[Player]:
        heading = soup.find(id="Current_roster")
        if not heading:
            return []
        table = heading.find_parent().find_next("table") if heading.find_parent() else None
        if not table:
            return []

        players = []
        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) < 3:
                continue
            role = self._clean_text(cells[0].get_text(" ", strip=True))
            name = self._clean_text(cells[2].get_text(" ", strip=True))
            if not self._looks_like_player_name(name):
                continue
            players.append(Player(name=name, role=role or None, image_url=None, source="Verified Roster"))
        return players

    def _scrape_espn_roster(self, team_name: str) -> list[Player]:
        slug = re.sub(r"[^a-z0-9]+", "-", team_name.lower()).strip("-")
        search_urls = [
            f"https://www.espn.com/search/_/q/{quote_plus(team_name)}",
            f"https://www.espn.com/{slug}/roster",
        ]
        players: list[Player] = []
        for url in search_urls:
            soup = self._get_soup(url)
            if not soup:
                continue
            for row in soup.select("tr"):
                cells = [self._clean_text(cell.get_text(" ", strip=True)) for cell in row.select("td")]
                if len(cells) < 2:
                    continue
                name = self._first_likely_name(cells)
                if not name:
                    continue
                image_url = self._extract_image_url(row, url)
                if image_url and not self._is_reachable_image(image_url):
                    image_url = None
                players.append(Player(name=name, role=self._first_role(cells), image_url=image_url, source="Verified Roster"))
            if players:
                break
        return players

    def _clean_players(self, players: list[Player]) -> list[Player]:
        seen = set()
        cleaned = []
        for player in players:
            name = self._clean_text(player.name)
            if not name or len(name) < 2 or name.lower() in seen:
                continue
            if any(token in name.lower() for token in ["roster", "coach", "staff", "statistics"]):
                continue
            seen.add(name.lower())
            cleaned.append(Player(name=name, role=player.role, image_url=player.image_url, source=player.source))
        return cleaned

    def _fallback_players(self) -> list[Player]:
        return [
            Player(name="Captain", role="Leader", image_url=None, source="Fallback"),
            Player(name="Forward", role="Forward", image_url=None, source="Fallback"),
            Player(name="Midfielder", role="Utility", image_url=None, source="Fallback"),
            Player(name="Defender", role="Defense", image_url=None, source="Fallback"),
            Player(name="Goalkeeper", role="Keeper", image_url=None, source="Fallback"),
        ]

    def _is_reachable_image(self, url: str) -> bool:
        try:
            response = requests.head(url, headers=DEFAULT_HEADERS, timeout=self.timeout, allow_redirects=True)
            if response.status_code >= 400:
                response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout, stream=True)
            return response.status_code < 400 and "image" in response.headers.get("content-type", "")
        except requests.RequestException:
            return False

    def _extract_image_url(self, row, base_url: str) -> str | None:
        image = row.select_one("img")
        if not image:
            return None
        src = image.get("src") or image.get("data-src")
        if not src:
            return None
        if src.startswith("//"):
            return f"https:{src}"
        return urljoin(base_url, src)

    def _first_likely_name(self, values: list[str]) -> str | None:
        for value in values:
            value = re.sub(r"^\d+\s*", "", value).strip()
            if self._looks_like_player_name(value):
                return value
        return None

    def _looks_like_player_name(self, value: str) -> bool:
        return bool(re.search(r"[A-Za-zÀ-ÿ]{2,}\s+[A-Za-zÀ-ÿ]{2,}", value))

    def _first_role(self, values: list[str]) -> str | None:
        role_tokens = {
            "guard",
            "forward",
            "center",
            "goalkeeper",
            "defender",
            "midfielder",
            "striker",
            "pitcher",
            "catcher",
            "quarterback",
            "running back",
        }
        for value in values:
            lowered = value.lower()
            if any(token in lowered for token in role_tokens):
                return value
        return None

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            return None

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" \n\t*")

    def _ipl_slug(self, team_name: str) -> str | None:
        lowered = self._clean_text(team_name).lower()
        if lowered in self.IPL_TEAMS:
            return self.IPL_TEAMS[lowered]
        for name, slug in self.IPL_TEAMS.items():
            if name in lowered or lowered in name:
                return slug
        return None