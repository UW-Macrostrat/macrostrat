CREATE TABLE IF NOT EXISTS public.usage_stats (
    id serial PRIMARY KEY,
    date timestamp with time zone NOT NULL DEFAULT now(),
    ip text NOT NULL,
    lat float NOT NULL,
    lng float NOT NULL
);