"""Print an actual forecast or ask a chatbot question about a synthetic customer."""
import argparse
import json
import sys
from backend.intelligence.data import ROOT, load_customer, load_daily
from backend.intelligence.service import analyze, analyze_horizons
from backend.intelligence.copilot import chat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['forecast', 'chat'])
    parser.add_argument('--customer', default='C002')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--question', default='Explain my financial risks and what I could change.')
    parser.add_argument('--provider', choices=['gemini', 'openai', 'offline'])
    parser.add_argument('--all-horizons', action='store_true', help='Compare 7/30/90 days from one consistent path.')
    parser.add_argument('--savings-floor', type=float, default=None)
    parser.add_argument('--fund-shortfalls-from-savings', action='store_true', help='Hypothetical reserve withdrawals; never moves money.')
    parser.add_argument('--indicators', help='JSON snapshot or economic report containing indicators; must not postdate customer as_of.')
    args = parser.parse_args()
    if args.command == 'chat' and (ROOT / '.env').exists():
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env', override=False)
    customer = load_customer(args.customer)
    if args.savings_floor is not None:
        customer['savings_floor'] = args.savings_floor
    if args.fund_shortfalls_from_savings:
        customer['fund_shortfalls_from_savings'] = True
    daily = load_daily()
    history = daily[daily.customer_id == args.customer]
    indicators = None
    if args.indicators:
        from pathlib import Path
        payload = json.loads(Path(args.indicators).read_text(encoding='utf-8'))
        indicators = payload.get('indicators', payload)
    if args.all_horizons:
        if args.command != 'forecast':
            parser.error('--all-horizons is only supported for forecast')
        results = analyze_horizons(customer, history, indicators=indicators)
        folder = ROOT / 'data/synthetic'
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f'{args.customer}-horizons.json'
        destination.write_text(json.dumps(results, indent=2, allow_nan=False), encoding='utf-8')
        print('Days   Variable spending   Ending checking   Minimum checking   Ending savings')
        for days, result in results.items():
            fc = result['forecast']
            print(f"{days:>4} {sum(r['spending'] for r in fc['daily']):19.2f} {fc['ending_balance']:17.2f} {fc['minimum_balance']:18.2f} {fc['ending_savings']:16.2f}")
            for warning in fc.get('warnings', []):
                print(f'  WARNING: {warning}')
            for alert in result['guardian']:
                print(f"  {alert['severity'].upper()}: {alert['id']} - {alert['explanation']} {json.dumps(alert['evidence'])}")
        print(f'Synthetic-data prototype; full results: {destination}')
        return
    analysis = analyze(customer, history, args.days, indicators)
    if args.command == 'chat':
        print('Preparing chatbot response; live providers may need several tool-call requests.', flush=True)
        try:
            response = chat(args.question, customer, analysis['forecast'], analysis, provider=args.provider)
        except KeyboardInterrupt:
            print('\nChat cancelled. No account changes were made.', file=sys.stderr)
            raise SystemExit(130)
        except Exception as error:
            # Only handle expected provider failures. Do not print raw exception text:
            # it can contain request URLs, headers, or provider data.
            import httpx
            if isinstance(error, httpx.TimeoutException):
                print('Chat request timed out. Run: .venv/Scripts/python.exe -m scripts.check_gemini', file=sys.stderr)
                raise SystemExit(1)
            if isinstance(error, httpx.TransportError):
                print('Chat connection failed. Check network/proxy settings and run scripts.check_gemini.', file=sys.stderr)
                raise SystemExit(1)
            from google.genai.errors import APIError
            if isinstance(error, APIError):
                if error.code in (500, 502, 503, 504):
                    hint = 'Google could not complete the request. Retry later; test a minimal request with scripts.check_gemini --generate.'
                else:
                    hint = 'Check key/project permissions, model availability, or quota in AI Studio.'
                print(f'Gemini returned HTTP {error.code}. {hint}', file=sys.stderr)
                raise SystemExit(1)
            raise
        print(f"Mode: {response['mode']}\n{response['answer']}")
        return
    fc = analysis['forecast']
    for warning in fc.get('warnings', []):
        print(f'WARNING: {warning}')
    print(f"Customer: {args.customer} | Model: {fc['model']} | Synthetic data | Horizon: {args.days} days")
    print(f"Starting checking: ${fc['starting_balance']:,.2f} | Minimum: ${fc['minimum_balance']:,.2f} | Ending: ${fc['ending_balance']:,.2f}")
    print(f"Ending savings: ${fc['ending_savings']:,.2f} | Reserve policy: {fc['reserve_policy']}")
    print('Date        Spending      Income       Bills     Balance')
    for row in fc['daily']:
        print(f"{row['date']}  {row['spending']:10.2f}  {row['income']:10.2f}  {row['bills']:10.2f}  {row['balance']:10.2f}")
    for alert in analysis['guardian']:
        print(f"ALERT [{alert['severity']}]: {alert['explanation']} {json.dumps(alert['evidence'])}")
    folder = ROOT / 'data/synthetic'
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f'{args.customer}-forecast-{args.days}.json'
    destination.write_text(json.dumps(analysis, indent=2, allow_nan=False), encoding='utf-8')
    print(f'Full forecast, health and Guardian output: {destination}')


if __name__ == '__main__':
    main()
