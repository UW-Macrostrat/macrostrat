CREATE TABLE IF NOT EXISTS model_feedback (
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