# FinPilot behavioral stress results

Synthetic behavioral stress tests. Passing expectations is NOT measured prediction accuracy.

Cases: 52/52 passed. Horizon-prefix check: PASS.

Controlled cases feed known scenario spending into the rules. ML cases load saved LightGBM models. Research cases refit the economic algorithms on deliberately modified FRED histories and retain abstention; their predictions are hypothetical sensitivity outputs.

| Case | Engine | Result | Economy / market | Forecast spending | Alerts or expected rejection |
| --- | --- | --- | --- | ---: | --- |
| healthy_control | controlled | PASS | steady / steady | 900.0 | none |
| overspending | controlled | PASS | steady / steady | 2400.0 | spending_above_budget, projected_spending_above_budget |
| budget_exact_120pct | controlled | PASS | steady / steady | 1200.0 | none |
| future_overspending | controlled | PASS | steady / steady | 3000.0 | projected_spending_above_budget |
| short_horizon_budget | controlled | PASS | steady / steady | 700.0 | none |
| low_cash | controlled | PASS | steady / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure |
| savings_crossing | controlled | PASS | steady / steady | 6000.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure, projected_spending_above_budget |
| no_implicit_savings | controlled | PASS | steady / steady | 6000.0 | low_balance, emergency_savings, payment_pressure, projected_spending_above_budget |
| inflation_tight | controlled | PASS | pressured / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure, cost_pressure_exposure |
| inflation_ample | controlled | PASS | pressured / steady | 900.0 | none |
| unemployment_rising | controlled | PASS | pressured / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure, income_resilience_exposure |
| unemployment_stable | controlled | PASS | steady / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure |
| high_rates_variable | controlled | PASS | pressured / steady | 900.0 | variable_rate_exposure |
| high_rates_fixed | controlled | PASS | pressured / steady | 900.0 | none |
| low_rates_not_loan_signal | controlled | PASS | steady / steady | 900.0 | none |
| market_near_term | controlled | PASS | steady / stressed | 900.0 | near_term_equity_exposure |
| market_long_term | controlled | PASS | steady / stressed | 900.0 | none |
| market_no_equity | controlled | PASS | steady / stressed | 900.0 | none |
| stale_market | controlled | PASS | steady / unknown | 900.0 | none |
| stale_all | controlled | PASS | unknown / unknown | 900.0 | none |
| future_observations | controlled | PASS | unknown / unknown | 900.0 | none |
| missing_economy | controlled | PASS | unknown / unknown | 900.0 | none |
| debt_tight | controlled | PASS | pressured / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure, debt_liquidity_tradeoff |
| debt_surplus | controlled | PASS | pressured / steady | 900.0 | debt_paydown_option |
| inflation_boundary | controlled | PASS | pressured / steady | 900.0 | none |
| rate_boundary | controlled | PASS | pressured / steady | 900.0 | none |
| drawdown_boundary | controlled | PASS | steady / stressed | 900.0 | none |
| negative_savings | controlled | PASS |  /  |  | savings_balance is out of range |
| nan_income | controlled | PASS |  /  |  | monthly_income must be finite numeric data |
| invalid_bill_day | controlled | PASS |  /  |  | bill day must be 1..31 |
| zero_income | controlled | PASS | steady / steady | 900.0 | savings_below_floor, low_balance, emergency_savings, payment_pressure |
| ml_pnc_7 | ml | PASS | steady / steady | 433.91 | none |
| ml_pnc_30 | ml | PASS | steady / steady | 3882.99 | projected_spending_above_budget |
| ml_pnc_90 | ml | PASS | steady / steady | 11449.11 | projected_spending_above_budget |
| ml_zero | ml | PASS | steady / steady | 9.67 | none |
| ml_irregular | ml | PASS | steady / steady | 3336.8 | none |
| ml_surge | ml | PASS | steady / steady | 20687.21 | projected_spending_above_budget |
| ml_one_off_spike | ml | PASS | steady / steady | 11931.68 | projected_spending_above_budget |
| ml_invalid_short | ml | PASS |  /  |  | Provide at least 29 consecutive daily observations for one customer |
| ml_invalid_gap | ml | PASS |  /  |  | Daily history must be unique and contiguous, including zero spending days |
| ml_invalid_duplicate | ml | PASS |  /  |  | Daily history must be unique and contiguous, including zero spending days |
| ml_invalid_nan | ml | PASS |  /  |  | Spending must be finite and nonnegative |
| ml_invalid_negative | ml | PASS |  /  |  | Spending must be finite and nonnegative |
| ml_invalid_horizon_0 | ml | PASS |  /  |  | days must be an integer from 1 to 90 |
| ml_invalid_horizon_91 | ml | PASS |  /  |  | days must be an integer from 1 to 90 |
| research_base | research | PASS | not_applicable / research_abstains |  | none |
| research_inflation_spike | research | PASS | not_applicable / research_abstains |  | none |
| research_labor_shock | research | PASS | not_applicable / research_abstains |  | none |
| research_rate_hike | research | PASS | not_applicable / research_abstains |  | none |
| research_market_crash | research | PASS | not_applicable / research_abstains |  | none |
| research_missing_month | research | PASS | not_applicable / research_abstains |  | none |
| research_short_history | research | PASS |  /  |  | Need at least 72 usable monthly feature rows |

## Actual model sensitivity outputs

| ML history | Serving method | 90-day spending | Change from PNC history forecast |
| --- | --- | ---: | ---: |
| pnc | lightgbm | 11449.11 | 0.0 |
| zero | lightgbm | 9.67 | -11439.44 |
| irregular | moving_average_28 | 3336.8 | -8112.31 |
| ml_irregular warning | Spending occurs much more frequently than in training data; using an unvalidated rolling-average fallback instead of the synthetic-calendar model. | | |
| surge | lightgbm | 20687.21 | 9238.1 |
| one_off_spike | lightgbm | 11931.68 | 482.57 |

| Economic history variant | Inflation estimate % | Unemployment estimate % | Uncalibrated P(up) |
| --- | ---: | ---: | ---: |
| base | 3.037 | 3.766 | 0.6786 |
| inflation_spike | 18.607 | 2.579 | 0.1811 |
| labor_shock | 3.063 | 4.773 | 0.7023 |
| rate_hike | 2.742 | 3.636 | 0.6703 |
| market_crash | 1.532 | 8.503 | 0.8514 |
| missing_month | 4.293 | 4.288 | 0.6053 |

## Alert guidance and actual scenario responses

### overspending

- **spending_above_budget**: Review optional spending categories and compare a spending-cut scenario while preserving essential bills.
- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $0.00.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $200.00; minimum checking changes by $0.00.

### future_overspending

- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $200.00; minimum checking changes by $0.00.

### low_cash

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.

### savings_crossing

- **savings_below_floor**: Projected savings falls below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $200.00; minimum checking changes by $200.00.

### no_implicit_savings

- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $200.00; minimum checking changes by $200.00.

### inflation_tight

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- **cost_pressure_exposure**: Test a 5% variable-cost increase, then identify optional purchases you could postpone. Preserve essential bills.
  Tradeoff: The 5% shock is illustrative, not an inflation forecast. Cutting essential spending may be harmful.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"cost_of_living_pct": 0.05}`: ending checking changes by $-45.00; minimum checking changes by $-21.00.

### unemployment_rising

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- **income_resilience_exposure**: Test a temporary 10% income reduction and check whether essential payments remain covered.
  Tradeoff: National unemployment changes do not predict this person losing income.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"income_reduction_pct": 0.1}`: ending checking changes by $-300.00; minimum checking changes by $-150.00.

### unemployment_stable

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.

### high_rates_variable

- **variable_rate_exposure**: Review the loan reset terms and test an illustrative one-percentage-point rate increase before adding debt.
  Tradeoff: Balance times rate/12 approximates interest exposure, not a lender payment quote. Existing fixed-rate payments are not changed.
- Tested `{"additional_monthly_expense": 10.0}`: ending checking changes by $-10.00; minimum checking changes by $0.00.

### market_near_term

- **near_term_equity_exposure**: Review whether near-term essential payments depend on selling investments. Compare the goal timing with available cash.
  Tradeoff: This is not a sell signal or portfolio-loss forecast. Market weakness alone does not justify changing all spending.

### debt_tight

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- **debt_liquidity_tradeoff**: Review required payments and preserve essential cash before testing extra repayment.
  Tradeoff: Extra debt payments reduce liquidity; they are not automatically helpful during economic stress.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $93.28.

### debt_surplus

- **debt_paydown_option**: Compare an optional extra debt payment with keeping the same amount liquid.
  Tradeoff: Check the simulated balance before acting; this model does not calculate future interest savings.
- Tested `{"extra_debt_payment": 100.0}`: ending checking changes by $-100.00; minimum checking changes by $0.00.

### zero_income

- **savings_below_floor**: Savings is already below your chosen reserve floor.
- **low_balance**: Projected checking falls below your chosen buffer.
- **emergency_savings**: Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.
- **payment_pressure**: A scheduled bill exceeds available modeled cash on its due date.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.
- Tested `{"monthly_spending_cut": 200}`: ending checking changes by $200.00; minimum checking changes by $200.00.

### ml_pnc_30

- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $200.00; minimum checking changes by $0.00.

### ml_pnc_90

- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $587.10; minimum checking changes by $0.00.

### ml_surge

- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $587.10; minimum checking changes by $587.10.

### ml_one_off_spike

- **projected_spending_above_budget**: Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.
- Tested `{"monthly_spending_cut": 200.0}`: ending checking changes by $587.10; minimum checking changes by $0.00.
