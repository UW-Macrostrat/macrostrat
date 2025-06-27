CREATE TABLE IF NOT EXISTS public.model_feedback (
    id serial PRIMARY KEY,
    checkin_id integer NOT NULL,
    photo_id integer NOT NULL,
    text_relevancy float NOT NULL,
    image_relevancy float NOT NULL,
    text_appropriateness float NOT NULL,
    image_appropriateness float NOT NULL,
    status_code integer NOT NULL,
    date_created timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.checkins
    ADD COLUMN model_run_id integer;

ALTER TABLE public.checkins
    ADD CONSTRAINT fk_model_run
        FOREIGN KEY (model_run_id)
        REFERENCES public.model_feedback(id)
        ON DELETE SET NULL;