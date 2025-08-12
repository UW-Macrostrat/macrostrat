CREATE SCHEMA IF NOT EXISTS user_features;

--removed rockd_jwt column
CREATE TABLE IF NOT EXISTS user_features.linked_strabo_account (
    id           serial PRIMARY KEY,
    person_id    integer NOT NULL UNIQUE
                 CONSTRAINT fk_user REFERENCES public."people" ON DELETE CASCADE,
    strabo_jwt   varchar NOT NULL
);

alter schema user_features OWNER TO "rockd";
alter table user_features.linked_strabo_account owner to "rockd";
grant insert, select, update on user_features.linked_strabo_account to web_anon;
