CREATE TABLE IF NOT EXISTS public.model_feedback (
    id serial PRIMARY KEY,
    checkin_id integer NOT NULL REFERENCES public.checkins(checkin_id) ON DELETE CASCADE,
    observation_id integer REFERENCES public.observations(obs_id),
    text_relevancy float,
    image_relevancy float NOT NULL,
    text_appropriateness float,
    image_appropriateness float NOT NULL,
    status_code integer NOT NULL,
    date_created timestamp with time zone NOT NULL DEFAULT now()
);