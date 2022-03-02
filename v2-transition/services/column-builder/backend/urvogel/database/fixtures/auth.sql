/* Authentication in db using postgrest  https://postgrest.org/en/stable/auth.html
Postgrest uses JWT to authenticate incoming requests, but the db can authorize db queries based 
on users.

Postgrest has a db centered system for handling incoming requests. A limited db role called 'authenticator' has 
the job to decrypt the incoming JWT and if correct, authenticator switches into the specified db role sent
in the request. If not correct, authenticator switces to 'anon' another db role that should be very limited.
With only the ability to login, or create a new user. Setting the names of anon and authenticator is done in 
a configuration file. The JWT secret for decoding must also be provided in the config.

authenticator is passed via db-uri
anon: db-anon-role (PGRST_DB_ANON_ROLE)
jwt-secret (PGRST_JWT_SECRET)

anon and authenticator must be privelges must be configured in db by superuser. 

In access control there is a distinction between application users and db users. Application users can 
be thought of as your client users logging in and may be in the thousands or more. db users are the ROLEs
that can be created and inherited. 

For our purposes we can combine both. We will map app users to db users in a general way. But we will also 
keep track of the projects, col, units, etc, that users can "SELECT, UPDATE, INSERT, DELETE". Generally, these
will be things that the user creates themselves. But they should also be able to give permissions to other users.

General DB roles:

postgres- the ultimate super-user
admin - can view, edit, create, and delete data and users
creator/owner - can view, edit, create and delete their own data and can create new users with permissions for their data

read-only - can only read specified data
read+write - can select, update and insert
read+write+delete - can select, update, insert and delete

Handle users in-database:

auth schema, users table
keep track of project ids that user can view data for in table.
Configure row level security by policies on table.


HOW LOGIN WORKS --> {
    take email and password,
    get the role and any other info we want tokenized,
    if login successful --> return json token
}

Generate JWT in SQL ---> pgjwt
https://github.com/michelp/pgjwt
https://app.bountysource.com/issues/89971002-example-code-to-show-how-to-install-pgjwt-extension-in-docker


How to access info on JWT for the current user --> to be user in policy creation::
current_setting('request.jwt.claims', true)::json->>'email';


*/


/* AUTH schema and functions */
DROP SCHEMA auth CASCADE;
CREATE SCHEMA auth;


/* necesary extenstions */
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pgjwt;

/* an auth user table */
CREATE TABLE IF NOT EXISTS 
auth.users(
  id     serial primary key,
  email  text check ( email ~* '^.+@.+\..+$' ),
  pass   text not null check (length(pass) < 512),
  role   name not null check (length(role) < 512)
);

/* Example of a basic data id to role */
CREATE TABLE IF NOT EXISTS
auth.user_projects(
  id serial primary key,
  user_ int REFERENCES auth.users(id),
  project int REFERENCES macrostrat.projects(id),
  role name not null check (length(role) < 512)
);

/* make sure the role being added to user table actually exists!! */
CREATE OR REPLACE FUNCTION
auth.check_role_exists() RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles AS r WHERE r.rolname = new.role) THEN
    raise foreign_key_violation USING message =
      'unknown database role: ' || new.role;
    RETURN NULL;
  END IF;
  RETURN new;
END
$$ LANGUAGE plpgsql;

DROP trigger IF EXISTS ensure_user_role_exists ON auth.users;
CREATE trigger ensure_user_role_exists
  BEFORE INSERT OR UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE PROCEDURE auth.check_role_exists();


/* Encrypt the password so it's not just sitting in the table */
CREATE OR REPLACE FUNCTION
auth.encrypt_pass() RETURNS trigger AS $$
BEGIN
  IF tg_op = 'INSERT' OR new.pass <> old.pass THEN
    new.pass := public.crypt(new.pass, public.gen_salt('md5'));
  END IF;
  RETURN new;
END
$$ LANGUAGE plpgsql;

DROP trigger IF EXISTS encrypt_pass ON auth.users;
CREATE trigger encrypt_pass
  BEFORE INSERT OR UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE PROCEDURE auth.encrypt_pass();


/* Access the stored role on a user -- used in login! 
*/
CREATE OR REPLACE FUNCTION
auth.user_role(email TEXT, pass TEXT) RETURNS name
  LANGUAGE plpgsql
  AS $$
BEGIN
  RETURN (
  SELECT role FROM auth.users
   WHERE users.email = user_role.email
     AND users.pass = public.crypt(user_role.pass, users.pass)
  );
END;
$$;

CREATE TYPE auth.jwt_token AS (
    token text
);

/* 
Login function! 
 */
CREATE OR REPLACE FUNCTION
macrostrat_api.login(email text, pass text) RETURNS auth.jwt_token AS $$
DECLARE
    _role name;
    result auth.jwt_token;
BEGIN
    SELECT auth.user_role(email, pass) INTO _role;
    IF _role IS NULL THEN
        raise invalid_password using message = 'invalid user or password';
    END IF;
    -- sign function comes from pgjwt extension. 
    SELECT sign(
            row_to_json(r), 'reallyreallyreallyreallyverysafesafesafesafe'
        ) AS token
        FROM (
            SELECT _role as role, login.email as email,
            extract(epoch FROM now())::integer + 60*60 AS exp 
        ) r
        INTO result;
    RETURN result;
END
$$ language plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION
macrostrat_api.create_user(email text, pass text) RETURNS BOOLEAN AS $$
DECLARE
  _role name;
BEGIN
  INSERT INTO auth.users(email, pass, role) 
    VALUES (email, public.crypt(pass, public.gen_salt('md5')), 'new_user');
  SELECT auth.user_role(email, pass) INTO _role;

  IF _role IS NULL THEN
    RETURN FALSE;
  END IF;

  RETURN TRUE;
END
$$ language plpgsql SECURITY DEFINER;


/*####################### BASE DB ROLES ##########################*/

-- these are the basic auth roles used by postgrest.
DROP ROLE IF EXISTS anon;
CREATE ROLE anon NOINHERIT;
DROP ROLE IF EXISTS authenticator;
CREATE ROLE authenticator NOINHERIT;
GRANT anon TO authenticator;

GRANT EXECUTE ON FUNCTION macrostrat_api.login(text,text) TO anon;
GRANT EXECUTE ON FUNCTION macrostrat_api.create_user(text, text) TO anon;

-- read only
DROP ROLE IF EXISTS reader;
CREATE ROLE reader NOINHERIT;
GRANT USAGE ON SCHEMA macrostrat_api TO reader;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO reader;

-- can read and insert/update but no delete
DROP ROLE IF EXISTS writer;
CREATE ROLE writer NOINHERIT;
GRANT USAGE ON SCHEMA macrostrat_api TO writer;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA macrostrat_api TO writer;

-- can delete as well as read and update/insert
DROP ROLE IF EXISTS deleter;
CREATE ROLE deleter NOINHERIT;
GRANT USAGE ON SCHEMA macrostrat_api TO deleter;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA macrostrat_api TO deleter;

-- can do everything including create new users, grant priviledges
DROP ROLE IF EXISTS owner_;
CREATE ROLE owner_ NOINHERIT;
GRANT USAGE ON SCHEMA macrostrat_api TO owner_;
GRANT USAGE ON SCHEMA auth TO owner_;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA macrostrat_api TO owner_;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth.users TO owner_;

-- a new user has only the option to create a new project
DROP ROLE IF EXISTS new_user;
CREATE ROLE new_user NOINHERIT;
GRANT USAGE ON SCHEMA macrostrat_api TO new_user;
GRANT USAGE ON SCHEMA macrostrat TO new_user;
GRANT USAGE ON SCHEMA auth TO new_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA macrostrat_api TO new_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA macrostrat TO new_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth.users TO new_user;

/* ################### Row level policies ################### */

/* function to get email off of jwt claims*/
CREATE OR REPLACE FUNCTION
macrostrat_api.get_email() returns text AS $$
DECLARE
  email_ text;
BEGIN
  SELECT current_setting('request.jwt.claims', true)::json->>'email' INTO email_;
RETURN email_;
END
$$language plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION
auth.user_project_insert() RETURNS trigger AS $$
DECLARE
  email_ text;
  id_
BEGIN
  IF tg_op = 'INSERT' THEN
    select macrostrat_api.get_email() into email_;
    select id from auth.users where users.email = email_ INTO id_;
    INSERT INTO auth.user_pojects(user, project, role_) 
      VALUES(id_, new.id, "owner_");
  END IF;
  RETURN new;
END
$$ LANGUAGE plpgsql;

DROP trigger IF EXISTS encrypt_pass ON auth.users;
CREATE trigger user_pojects
  AFTER INSERT ON macrostrat.projects
  FOR EACH ROW
  EXECUTE PROCEDURE auth.user_project_insert();


CREATE OR REPLACE FUNCTION
macrostrat_api.current_user_projects() RETURNS TABLE(id int) AS $$
DECLARE
  email_ text;
BEGIN
  SELECT macrostrat_api.get_email() INTO email_;
  RETURN QUERY
    SELECT project FROM auth.user_projects
    JOIN auth.users u
    on u.email = email_;
END
$$ language plpgsql SECURITY DEFINER;

ALTER TABLE macrostrat.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_ ON macrostrat.projects FOR SELECT
USING (id IN (SELECT macrostrat_api.current_user_projects()));