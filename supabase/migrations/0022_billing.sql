-- 0022 — Stripe billing: subscriptions + refund requests + payment ledger.
--
-- Design notes:
--   * Subscriptions are per-USER (not per-org). Each row is the current view
--     of the user's Stripe subscription; webhooks keep it in sync.
--   * `tier` is the app's business-level tier, not the Stripe price id, so we
--     can rename price IDs without touching every row: 'oi' (Opportunity
--     Intelligence, $49), 'full' (Full Capture, $99, the recommended tier),
--     'enterprise' (Enterprise, contact-us). 'free' means no active sub.
--   * `interval` mirrors Stripe: 'month' or 'year'.
--   * `status` mirrors Stripe subscription status verbatim ('active',
--     'trialing', 'past_due', 'canceled', 'incomplete', 'unpaid').
--   * A user may only ever have ONE row here — unique on user_id.

create table if not exists user_subscriptions (
    user_id                 uuid primary key references users(id) on delete cascade,
    tier                    text not null default 'free',
    interval                text not null default 'month',
    status                  text not null default 'free',
    stripe_customer_id      text not null default '',
    stripe_subscription_id  text not null default '',
    current_period_end      timestamptz,
    cancel_at_period_end    boolean not null default false,
    canceled_at             timestamptz,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now()
);
create index if not exists idx_user_sub_customer on user_subscriptions (stripe_customer_id);
create index if not exists idx_user_sub_sub      on user_subscriptions (stripe_subscription_id);

-- Every checkout attempt / one-off charge that flows through /api/payments. We
-- use this as the idempotency + polling source of truth; the webhook and
-- status endpoint both update the SAME row using $ne 'paid' guards.
create table if not exists payment_transactions (
    id                        uuid primary key default gen_random_uuid(),
    session_id                text unique not null,
    user_id                   uuid references users(id) on delete set null,
    lookup_key                text not null default '',      -- price lookup key
    amount_cents              bigint not null default 0,
    currency                  text not null default 'usd',
    status                    text not null default 'initiated',  -- initiated|completed|failed|expired|refunded
    payment_status            text not null default 'pending',    -- pending|paid|refunded|failed|expired
    stripe_subscription_id    text not null default '',
    stripe_payment_intent_id  text not null default '',
    stripe_charge_id          text not null default '',
    created_at                timestamptz not null default now(),
    updated_at                timestamptz not null default now()
);

-- Refund-request workflow (user asks → CaptureAgent approves & issues via Stripe).
create table if not exists refund_requests (
    id                       uuid primary key default gen_random_uuid(),
    user_id                  uuid not null references users(id) on delete cascade,
    email                    text not null,
    subscription_id          text not null default '',   -- Stripe sub id at request time
    payment_intent_id        text not null default '',   -- last invoice PI
    charge_id                text not null default '',
    amount_cents_requested   bigint not null default 0,  -- 0 = full refund
    amount_cents_refunded    bigint not null default 0,
    reason                   text not null default '',
    admin_notes              text not null default '',
    status                   text not null default 'pending'
        check (status in ('pending','approved','denied','failed')),
    stripe_refund_id         text not null default '',
    requested_at             timestamptz not null default now(),
    decided_at               timestamptz,
    decided_by               uuid references users(id) on delete set null
);
create index if not exists idx_refund_status on refund_requests (status, requested_at desc);
