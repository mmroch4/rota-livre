-- Rota Livre: database for barrier reports and "it's gone" answers (Supabase Postgres).
-- Run once in Supabase → SQL Editor. Safe to re-run: everything is "if not exists" / "or replace".
-- Coreflux writes here through its PostgreSQL connector (lot/10-barriers-db.lotnb) as the
-- coreflux_writer role created at the end; see db/README.md.

-- One row per barrier reported in the web app (MQTT access/barriers/<id>).
create table if not exists public.barriers (
    id           text primary key check (id ~ '^b[0-9a-z]{4,40}$'),
    kind         text not null check (kind in
                     ('works', 'blocked_sidewalk', 'parked_car', 'broken_lift', 'damaged_pavement', 'other')),
    description  text not null default '' check (length(description) <= 280),
    lat          double precision not null check (lat between -90 and 90),
    lon          double precision not null check (lon between -180 and 180),
    reported_at  timestamptz not null,
    expires_at   timestamptz not null,
    received_at  timestamptz not null default now(), -- when Coreflux stored it
    deleted_at   timestamptz                          -- set when its reporter deleted it ("Apagar o meu reporte")
);

-- One row per "Já não está" answer (MQTT access/barriers/<barrier id>/feedback). Never removes a barrier:
-- the team reviews the counts at the end of the day. No foreign key on purpose: an answer may concern a
-- barrier that was published by another source and is not in this table.
create table if not exists public.barrier_feedback (
    id           text primary key check (id ~ '^f[0-9a-z]{4,40}$'),
    barrier_id   text not null check (barrier_id ~ '^b[0-9a-z]{4,40}$'),
    answer       text not null check (answer in ('gone')),
    answered_at  timestamptz not null,
    lat          double precision check (lat between -90 and 90),   -- where the person was, when known
    lon          double precision check (lon between -180 and 180),
    received_at  timestamptz not null default now()
);
create index if not exists barrier_feedback_barrier_id_idx on public.barrier_feedback (barrier_id);
create index if not exists barrier_feedback_answered_at_idx on public.barrier_feedback (answered_at);

-- End-of-day review: every barrier that is still listed, with its "gone" answers.
create or replace view public.barrier_review with (security_invoker = true) as
select
    b.id,
    b.kind,
    b.description,
    b.lat,
    b.lon,
    b.reported_at,
    b.expires_at,
    count(f.id)                                                   as gone_answers_total,
    count(f.id) filter (where f.answered_at >= date_trunc('day', now())) as gone_answers_today,
    max(f.answered_at)                                            as last_gone_answer_at
from public.barriers b
left join public.barrier_feedback f on f.barrier_id = b.id
where b.deleted_at is null
group by b.id
order by gone_answers_today desc, gone_answers_total desc, b.reported_at desc;

-- Supabase also exposes tables through its public REST API. Row level security with no policy for the
-- anon/authenticated roles keeps that API closed: only the roles below can read or write.
alter table public.barriers enable row level security;
alter table public.barrier_feedback enable row level security;

-- The database user Coreflux connects as: it can add and update barriers and add answers, nothing else.
-- Replace the password below before running (and put the same one in the broker as a secret).
do $$
begin
    if not exists (select from pg_roles where rolname = 'coreflux_writer') then
        create role coreflux_writer login password 'CHANGE-ME-BEFORE-RUNNING';
    end if;
end
$$;
grant usage on schema public to coreflux_writer;
grant select, insert, update on public.barriers to coreflux_writer;
grant select, insert on public.barrier_feedback to coreflux_writer; -- select: ON CONFLICT needs to read the id

drop policy if exists coreflux_writes_barriers on public.barriers;
create policy coreflux_writes_barriers on public.barriers
    for all to coreflux_writer using (true) with check (true);

drop policy if exists coreflux_adds_feedback on public.barrier_feedback;
create policy coreflux_adds_feedback on public.barrier_feedback
    for insert to coreflux_writer with check (true);
drop policy if exists coreflux_reads_feedback on public.barrier_feedback;
create policy coreflux_reads_feedback on public.barrier_feedback
    for select to coreflux_writer using (true);
