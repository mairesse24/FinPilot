"""Check Gemini model access without sending financial data or generating text."""
import os
import sys
import argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
import httpx
from backend.intelligence.data import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true', help='Also request a short OK response; uses generation quota.')
    parser.add_argument('--model', help='Test a model without changing .env.')
    parser.add_argument('--list-models', action='store_true', help='List model names available to this key without generating text.')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env', override=False)
    key, model = os.getenv('GEMINI_API_KEY'), args.model or os.getenv('GEMINI_MODEL')
    if not key or not model:
        print('Set GEMINI_API_KEY and GEMINI_MODEL in .env.', file=sys.stderr)
        return 1
    print(('Listing available models' if args.list_models else f'Checking model metadata for {model}')
          + '; one attempt, 10-second request timeout.', flush=True)
    stage = 'model listing' if args.list_models else 'model metadata'
    try:
        with genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=10000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
            if args.list_models:
                for item in client.models.list():
                    if 'generateContent' in (item.supported_actions or []):
                        print(item.name)
                return 0
            metadata = client.models.get(model=model)
            print('Model metadata access confirmed.', flush=True)
            if args.generate:
                stage = 'minimal generation'
                print('Checking minimal text generation.', flush=True)
                response = client.models.generate_content(model=model, contents='Reply with the word OK.',
                    config=types.GenerateContentConfig(max_output_tokens=256))
                if not response.text:
                    print('Generation returned no text.', file=sys.stderr)
                    return 1
                print('PASS: a minimal text-generation request returned text.')
        print(f'PASS: Google returned metadata for {metadata.name}.' + ('' if args.generate else ' Text generation is not tested by this check.'))
        return 0
    except errors.APIError as error:
        if error.code in (500, 502, 503, 504):
            hint = 'Google service failed or timed out; retry later. This does not establish an invalid key.'
        else:
            hint = 'Check key/project access for 400/401/403, model availability for 404, and quota for 429.'
        print(f'Google returned HTTP {error.code}. {hint}', file=sys.stderr)
    except httpx.TimeoutException:
        print(f'{stage.capitalize()} request timed out. Check network, proxy, or Google availability; a timeout does not establish key validity.', file=sys.stderr)
    except httpx.TransportError:
        print('Connection failed. Check network, proxy, firewall, and TLS configuration. Key validity is unconfirmed.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nCheck cancelled.', file=sys.stderr)
        raise SystemExit(130)
