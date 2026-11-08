CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text NOT NULL,
  safety_buffer NUMERIC(14,2) NOT NULL DEFAULT 500,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  account_type text NOT NULL CHECK (account_type IN ('checking','savings','credit_card','loan')),
  balance NUMERIC(14,2) NOT NULL,
  apr NUMERIC(8,4),
  min_payment NUMERIC(14,2),
  credit_limit NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  amount NUMERIC(14,2) NOT NULL,
  category text NOT NULL,
  date date NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, date);

CREATE TABLE IF NOT EXISTS recurring_bills (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  amount NUMERIC(14,2) NOT NULL,
  category text NOT NULL,
  frequency text NOT NULL CHECK (frequency IN ('weekly','biweekly','monthly')),
  due_date date NOT NULL
);

CREATE TABLE IF NOT EXISTS income_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  amount NUMERIC(14,2) NOT NULL,
  frequency text NOT NULL CHECK (frequency IN ('weekly','biweekly','monthly')),
  next_pay_date date NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date date NOT NULL,
  health_score NUMERIC(5,2),
  total_balance NUMERIC(14,2),
  UNIQUE (user_id, date)
);

CREATE TABLE IF NOT EXISTS risk_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date date NOT NULL,
  rule text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('low','medium','high')),
  title text NOT NULL,
  detail jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE income_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_alerts ENABLE ROW LEVEL SECURITY;
