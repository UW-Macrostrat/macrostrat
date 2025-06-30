CREATE TABLE IF NOT EXISTS public.model_feedback (
    id serial PRIMARY KEY,
    checkin_id integer NOT NULL REFERENCES public.checkins(checkin_id),
    observation_id integer NOT NULL REFERENCES public.observations(obs_id),
    photo_id integer NOT NULL REFERENCES public.observations(photo),
    text_relevancy float NOT NULL,
    image_relevancy float NOT NULL,
    text_appropriateness float NOT NULL,
    image_appropriateness float NOT NULL,
    status_code integer NOT NULL,
    date_created timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.observations
    ADD COLUMN model_run_id integer REFERENCES public.model_feedback(id);

ALTER TABLE public.checkins
    ADD COLUMN model_run_id integer REFERENCES public.model_feedback(id);