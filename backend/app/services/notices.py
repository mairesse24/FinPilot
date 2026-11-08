"""Compatibility boundary: legacy warning text -> stable, scoped UI notices.

Raw strings remain diagnostic evidence. Unknown engineering failures never become
user-facing stack traces. Calculation providers can migrate to explicit codes.
"""
import hashlib
from app.schemas.common import Notice

# Match full technical fragments without splitting on semicolons inside a notice.
RULES = [
 ('Configured PostgreSQL unavailable', 'data_source_substituted','critical',
  'The configured database is unavailable. Generated demo records are being shown instead of your configured financial data.'),
 ('failed to import', 'calculation_fallback','critical',
  'A calculation service was unavailable. A simpler method is being used; review its limitations.'),
 (' raised ', 'calculation_fallback','critical',
  'A calculation service was unavailable. A simpler method is being used; review its limitations.'),
 ('Spending occurs much more frequently', 'forecast_pattern_shift','critical',
  "Your recent spending pattern differs from the model's training data, so we're using a simpler estimate. Forecast confidence is limited."),
 ('Forecast abstained', 'forecast_unavailable','critical',
  'Forecast abstained: more spending history or a confirmed budget is needed. Future balances are unavailable.'),
 ('Only ', 'forecast_short_history','critical',
  'There is little spending history. This estimate is uncertain and may miss upcoming purchases.'),
 ('Fewer than 90 history days', 'forecast_support_unknown','data_limitation',
  'There is not enough history to check whether this spending pattern fits the forecasting model.'),
 ('approved loan has no confirmed', 'loan_balance_missing','critical',
  'A loan balance is missing. Displayed debt may be understated and net worth overstated.'),
 ('No confirmed future income', 'income_schedule_missing','critical',
  'Upcoming income is not confirmed, so the cash forecast includes no future deposits.'),
 ('No confirmed future bills', 'bill_schedule_missing','critical',
  'Upcoming bills are not confirmed. The forecast may overstate available cash.'),
 ('aggregate floor', 'debt_linkage_incomplete','data_limitation',
  'Some debt payments cannot be matched to their accounts. Debt burden is an estimate.'),
 ('unavailable components are omitted', 'legacy_score_partial','data_limitation',
  'This prototype health score uses available information; missing factors are excluded and the remaining weights are adjusted. It is not a credit score.'),
 ('Nessie sandbox snapshot', 'bank_snapshot','data_limitation',
  'Bank records are a saved sandbox snapshot. Reloading analysis does not fetch new bank activity.'),
 ('Loan balances require', 'loan_principal_policy','diagnostic',
  'Original loan amounts are not used as current debt balances.'),
 ('Loan payment dates', 'loan_calendar','data_limitation',
  'Loan payment dates must be confirmed before they can appear in the cash forecast.'),
 ('Internal transfers, credit-card', 'spending_scope','data_limitation',
  'Spending totals cover checking purchases. Transfers, card activity and cash withdrawals are excluded.'),
 ('ATM withdrawals excluded', 'cash_usage_unknown','data_limitation',
  'Cash withdrawals are excluded because later cash purchases are not recorded.'),
 ('Card activity excluded', 'card_settlement_scope','data_limitation',
  'Card purchases are excluded from checking forecasts; confirmed card payments are needed.'),
 ('Checking deposits are shown', 'deposits_unverified','data_limitation',
  'Deposits are money received, not confirmed salary or a promise of future income.'),
 ('Unmapped purchases use', 'purchases_unclassified','data_limitation',
  'Some purchases are uncategorized. Identify bill payments so they are not counted again as future variable spending.'),
 ('residual calibration was evaluated only', 'interval_horizon','data_limitation',
  'Longer-range forecast bands have not been calibrated. Treat them as stress scenarios.'),
]


def merge_notices(*groups):
    unique={}
    for group in groups:
        for notice in group:
            key=(notice.code,notice.context)
            if key not in unique:unique[key]=notice
            elif notice.technical_detail not in unique[key].technical_detail:
                unique[key]=unique[key].model_copy(update={'technical_detail':unique[key].technical_detail+'\n'+notice.technical_detail})
    return list(unique.values())


def notices_for(warnings,context):
    result=[]
    for detail in warnings:
        if not detail:continue
        matched=False
        for needle,code,category,message in RULES:
            if needle in detail:
                matched=True
                result.append(Notice(code=code,context=context,category=category,message=message,technical_detail=detail))
        if not matched:
            code='diagnostic_'+hashlib.sha256(detail.encode()).hexdigest()[:12]
            result.append(Notice(code=code,context=context,category='diagnostic',
                                 message='Engineering diagnostic',technical_detail=detail))
    return merge_notices(result)


def with_profile_notices(meta,profile):
    return meta.model_copy(update={'notices':merge_notices(meta.notices,
        notices_for([meta.warning],'analysis'),notices_for(profile.data_warnings,'bank_data'))})
