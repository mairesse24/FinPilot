"""Server-only provider configuration; public summaries never contain credentials."""
import os
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[2]


def load_config():
    return {**dotenv_values(ROOT/'.env'),**dotenv_values(ROOT/'backend/.env'),**os.environ}


def summary():
    config=load_config();provider=config.get('COPILOT_PROVIDER','offline').lower()
    prefix=provider.upper()
    duplicates=[]
    for path in (ROOT/'.env',ROOT/'backend/.env'):
        if not path.exists():continue
        count=sum(line.strip().startswith('COPILOT_PROVIDER=') for line in path.read_text(encoding='utf-8').splitlines())
        if count>1:duplicates.append(str(path.relative_to(ROOT)))
    return {'provider':provider,'model':config.get(prefix+'_MODEL'),
            'key_configured':bool(config.get(prefix+'_API_KEY')) if provider!='offline' else False,
            'duplicate_provider_files':duplicates}


def safe_failure(exc):
    status=getattr(exc,'status_code',None)
    if not isinstance(status,int):status=getattr(exc,'code',None)
    status=status if isinstance(status,int) else None
    code=getattr(exc,'code',None)
    if code in ('insufficient_quota','credit_balance_exhausted','organization_usage_limit_exceeded','spend_limit_exceeded'):
        return 'quota_exhausted','The AI provider reports exhausted credits or a spending limit. Review API billing; the local calculation-based assistant is still available.'
    if status==401:return 'authentication_failed','The AI provider rejected the API key. Replace it privately in the backend environment.'
    if status==403:return 'access_denied','The API key does not have permission for this AI request.'
    if status==404:return 'model_unavailable','The configured AI model is unavailable to this API key.'
    if status==429:return 'rate_limited','The AI provider is temporarily rate-limiting requests. Try again later.'
    if status and status>=500:return 'provider_unavailable','The AI provider could not complete the request. Try again later.'
    if 'timeout' in type(exc).__name__.lower():return 'timeout','The AI request timed out. The local calculation-based assistant is still available.'
    return 'provider_error','Live AI could not complete the request. A local calculation-based response is being used.'
