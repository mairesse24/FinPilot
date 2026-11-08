"""Check configured OpenAI access without customer data or credential output."""
import argparse
import json
from backend.intelligence.provider_config import load_config,summary,safe_failure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate',action='store_true',help='Also make one minimal generation request to check generation access/quota.')
    args=parser.parse_args();config=load_config()
    print(json.dumps(summary(),indent=2))
    key=config.get('OPENAI_API_KEY');model=config.get('OPENAI_MODEL')
    if not key or not model:
        print('Set OPENAI_API_KEY and OPENAI_MODEL privately.');return 1
    from openai import OpenAI
    try:
        with OpenAI(api_key=key,timeout=12,max_retries=0) as client:
            client.models.retrieve(model)
            print('Model metadata access succeeded; this alone does not establish available generation credits.')
            if args.generate:
                r=client.responses.create(model=model,input='Reply OK.',max_output_tokens=16,store=False)
                print('Minimal generation returned text.' if r.output_text else 'Generation returned no text.')
        return 0
    except Exception as exc:
        code,message=safe_failure(exc)
        print(json.dumps({'result':'failed','code':code,'message':message}));return 1


if __name__=='__main__':raise SystemExit(main())
