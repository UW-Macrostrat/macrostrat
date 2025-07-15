CREATE TABLE IF NOT EXISTS public.rockd_coords (
    date_created timestamp with time zone NOT NULL DEFAULT now() PRIMARY KEY,
    latitude float NOT NULL,
    longitude float NOT NULL,
);