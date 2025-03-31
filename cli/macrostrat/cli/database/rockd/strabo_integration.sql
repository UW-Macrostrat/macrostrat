CREATE SCHEMA user_features

create table user_features.linked_strabo_account
(
    id              serial primary key,
    person_id        integer not null constraint fk_user references public."people" on delete cascade,
    strabo_jwt        varchar(120) not null
);

alter table user_features.linked_strabo_account owner to "macrostrat-admin";
grant insert, select, update on user_features.linked_strabo_account to web_anon;
