from typing import Iterable, Generator
import time
import requests
from itertools import chain

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda *args, **kwargs: args[0]

BASE_URL = "api.the-odds-api.com/v4"
PROTOCOL = "https://"


class APIException(RuntimeError):
    def __str__(self):
        return f"('{self.args[0]}', '{self.args[1].json()['message']}')"


class AuthenticationException(APIException):
    pass


class RateLimitException(APIException):
    pass


def handle_faulty_response(response: requests.Response):
    if response.status_code == 401:
        raise AuthenticationException("Failed to authenticate with the API. is the API key valid?", response)
    elif response.status_code == 429:
        raise RateLimitException("Encountered API rate limit.", response)
    else:
        raise APIException("Unknown issue arose while trying to access the API.", response)


def get_sports(key: str) -> set[str]:
    url = f"{BASE_URL}/sports/"
    escaped_url = PROTOCOL + requests.utils.quote(url)
    querystring = {"apiKey": key}

    response = requests.get(escaped_url, params=querystring)
    if not response:
        handle_faulty_response(response)

    return {item["key"] for item in response.json()}


def get_data(key: str, sport: str, region: str = "eu"):
    url = f"{BASE_URL}/sports/{sport}/odds/"
    escaped_url = PROTOCOL + requests.utils.quote(url)
    querystring = {
        "apiKey": key,
        "regions": region,
        "oddsFormat": "decimal",
        "dateFormat": "unix"
    }

    response = requests.get(escaped_url, params=querystring)
    if not response:
        handle_faulty_response(response)

    return response.json()


def process_data(matches: Iterable, include_started_matches: bool = True) -> Generator[dict, None, None]:
    """Extracts all matches that are available and calculates some things about them, such as the time to start and
    the best available implied odds."""
    matches = tqdm(matches, desc="Checking all matches", leave=False, unit=" matches")
    for match in matches:
        start_time = int(match["commence_time"])
        if not include_started_matches and start_time < time.time():
            continue

        best_odd_per_outcome = {}
        for bookmaker in match["bookmakers"]:
            bookie_name = bookmaker["title"]
            for outcome in bookmaker["markets"][0]["outcomes"]:
                outcome_name = outcome["name"]
                odd = outcome["price"]
                if outcome_name not in best_odd_per_outcome.keys() or \
                        odd > best_odd_per_outcome[outcome_name][1]:
                    best_odd_per_outcome[outcome_name] = (bookie_name, odd)

        total_implied_odds = sum(1 / i[1] for i in best_odd_per_outcome.values())
        match_name = f"{match['home_team']} v. {match['away_team']}"
        time_to_start = (start_time - time.time()) / 3600
        league = match["sport_key"]
        yield {
            "match_name": match_name,
            "match_start_time": start_time,
            "hours_to_start": time_to_start,
            "league": league,
            "best_outcome_odds": best_odd_per_outcome,
            "total_implied_odds": total_implied_odds,
        }


def get_arbitrage_opportunities(key: str, region: str, cutoff: float, sports: list, live: bool, unit: float):
    all_sports = get_sports(key)

    # filter by key from returned available sports
    if sports is not None and len(sports):
        all_sports = {item for item in all_sports if any(search_string in item for search_string in sports)}

    data = chain.from_iterable(get_data(key, sport, region=region) for sport in all_sports)
    data = filter(lambda x: x != "message", data)
    results = process_data(data, live)
    arbitrage_opportunities = filter(lambda x: 0 < x["total_implied_odds"] < 1 - cutoff, results)
    arbitrage_opportunities_list = list(arbitrage_opportunities)
    # add the bet amounts
    for match in arbitrage_opportunities_list:
        match["max_profit"] = {"amount": -8675309, "bet": ""}
        match["min_profit"] = {"amount": -8675309, "bet": ""}
        for outcome, odds in match["best_outcome_odds"].items():
            individual_arb = (1 / odds[1])
            updated_odds = {
                "platform": odds[0],
                "odds": odds[1],
                "bet_amount": round((individual_arb * unit) / match["total_implied_odds"], 2)
            }
            other_bet_totals = unit - updated_odds["bet_amount"]
            return_amount = round(
                (round(updated_odds["bet_amount"] * (updated_odds["odds"] - 1), 2)) - other_bet_totals, 2)

            #  set the min return if first
            if match["min_profit"]["amount"] == -8675309:
                match["min_profit"] = {"amount": return_amount, "bet": outcome}
            #  set the max return if first
            if match["max_profit"]["amount"] == -8675309:
                match["max_profit"] = {"amount": return_amount, "bet": outcome}

            if return_amount > match["max_profit"]["amount"]:
                match["max_profit"] = {"amount": return_amount, "bet": outcome}
            if return_amount < match["min_profit"]["amount"]:
                match["min_profit"] = {"amount": return_amount, "bet": outcome}
            match["best_outcome_odds"][outcome] = updated_odds

    return arbitrage_opportunities_list
