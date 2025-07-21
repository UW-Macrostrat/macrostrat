/* 1 ─ Add the new column (type timestamptz is the usual choice) */
ALTER TABLE public.people
  ADD COLUMN token_exp timestamptz;

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
