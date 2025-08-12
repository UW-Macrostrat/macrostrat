/* 1 ─ Add the new column (type timestamptz is the usual choice) */
DO $$
DECLARE
  k_people text;
  k_checkins text;
  k_obs text;
BEGIN
  SELECT c.relkind INTO k_people
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname='people';

  SELECT c.relkind INTO k_checkins
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname='checkins';

  SELECT c.relkind INTO k_obs
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname='observations';

  IF k_people IS NULL OR k_checkins IS NULL OR k_obs IS NULL THEN
    RAISE EXCEPTION
      'rockd_initial_schema precheck failed. db=% user=% | people=% checkins=% observations=%',
      current_database(), current_user, k_people, k_checkins, k_obs;
  END IF;
END$$;

ALTER TABLE public.people
  ADD COLUMN IF NOT EXISTS token_exp timestamptz;

INSERT INTO public.people (
    first_name,
    last_name,
    email,
    password,
    public,
    created,
    save_photos,
    oauth_type,
    oauth_id,
    autocorrect,
    affiliation,
    orc_id,
    last_notification_check,
    last_data_dump,
    token_exp
)
VALUES (
    'Internal ML Model',                                         -- first_name
    'Integrations',                                              -- last_name
    'integrations@internal.com',                                 -- email
    '$2a$08$iaME/tEwdU.0Rz8ZsCr5gejANP2r2Pldy4a06lF.jvP4jVjg5Pdni', -- bcrypt
    TRUE,                                                        -- public
    NOW(),                                                       -- created
    TRUE,                                                        -- save_photos
    NULL,                                                        -- oauth_type
    NULL,                                                        -- oauth_id
    FALSE,                                                       -- autocorrect
    'Internal',                                                  -- affiliation
    '',                                                          -- orc_id
    NOW(),                                                       -- last_notification_check
    NULL,                                                        -- last_data_dump
    NOW() + INTERVAL '1 year'                                    -- token_exp
);
