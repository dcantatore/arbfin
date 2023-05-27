"""A simple tool to find sports betting arbitrage opportunities.

The tool fetches the odds from The Odds API (https://the-odds-api.com/) and compares the odds at different
bookmakers to each other in order to determine whether there are profitable and risk-free bets available."""
from src.logic import get_arbitrage_opportunities
import os
import argparse
from dotenv import load_dotenv
from rich import print


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="Arbitrage Finder",
        description=__doc__
    )
    parser.add_argument(
        "-k", "--key",
        default=os.environ.get("API_KEY"),
        help="The API key from The Odds API. If left blank it will default to the value of $API_KEY."
    )
    parser.add_argument(
        "-r", "--region",
        choices=["eu", "us", "au", "uk"],
        default=os.environ.get("REGION"),
        help="The region in which to look for arbitrage opportunities."
    )
    parser.add_argument(
        "-u", "--unformatted",
        action="store_true",
        help="If set, turn output into the json dump from the opportunities."
    )
    parser.add_argument(
        "-c", "--cutoff",
        type=float,
        default=os.environ.get("CUTOFF"),
        help="The minimum profit margin required for an arb to be displayed. Inputted as a percentage."
    )
    parser.add_argument(
        "-s", "--sports",
        type=str,
        default=os.environ.get("SPORTS"),
        help="If set it will only check these sports, please see readme for more details. For cli use format such as "
             "-s \"mma_mixed_martial_arts americanfootball_nfl\""
    )
    parser.add_argument(
        "-l", "--live",
        type=str,
        default=os.environ.get("LIVE"),
        help="This defaults to true, set to false to not check live sports. Accepts string as true | false"
    )

    args = parser.parse_args()

    if not args.cutoff:
        args.cutoff = 10

    if not args.region:
        args.region = 'us'

    if args.live:
        live = args.live == "true"
    else:
        live = True

    cutoff = args.cutoff / 100

    if args.sports:
        args.sports = args.sports.split(" ")

    arbitrage_opportunities = get_arbitrage_opportunities(key=args.key, region=args.region, cutoff=cutoff,
                                                          sports=args.sports, live=live)

    if args.unformatted:
        print(list(arbitrage_opportunities))
    else:
        arbitrage_opportunities = list(arbitrage_opportunities)
        print(f"In region {args.region} with {args.cutoff} percent margin")
        print(
            f"{len(arbitrage_opportunities)} arbitrage opportunities found {':money-mouth_face:' if len(arbitrage_opportunities) > 0 else ':man_shrugging:'}")

        for arb in arbitrage_opportunities:
            print(f"\t[italic]{arb['match_name']} in {arb['league']} [/italic]")
            print(f"\t\tTotal implied odds: {arb['total_implied_odds']} with these odds:")
            for key, value in arb['best_outcome_odds'].items():
                print(f"\t\t[bold red]{key}[/bold red] with [green]{value[0]}[/green] for {value[1]}")


if __name__ == '__main__':
    main()
