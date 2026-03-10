ALTER TABLE public.checkins
ADD COLUMN IF NOT EXISTS spot_id bigint DEFAULT NULL;

