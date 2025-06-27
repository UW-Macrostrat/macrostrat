CREATE TABLE IF NOT EXISTS public.model_feedback (
    id serial PRIMARY KEY,
    checkin_id integer,
    observation_id integer,
    photo_id integer NOT NULL,
    text_relevancy float NOT NULL,
    image_relevancy float NOT NULL,
    text_appropriateness float NOT NULL,
    image_appropriateness float NOT NULL,
    status_code integer NOT NULL,
    date_created timestamp with time zone NOT NULL DEFAULT now()
    CHECK (
        (checkin_id IS NOT NULL AND observation_id IS NULL) OR
        (checkin_id IS NULL AND observation_id IS NOT NULL)
    )
);

ALTER TABLE public.observations
    ADD COLUMN model_run_id integer;

ALTER TABLE public.observations
    ADD COLUMN status integer;

ALTER TABLE public.observations
    ADD CONSTRAINT fk_model_run
        FOREIGN KEY (model_run_id)
        REFERENCES public.model_feedback(id)
        ON DELETE SET NULL;

ALTER TABLE public.checkins
    ADD COLUMN model_run_id integer;

ALTER TABLE public.checkins
    ADD CONSTRAINT fk_model_run
        FOREIGN KEY (model_run_id)
        REFERENCES public.model_feedback(id)
        ON DELETE SET NULL;