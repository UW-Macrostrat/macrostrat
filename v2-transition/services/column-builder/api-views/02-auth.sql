/* Authentication in db using postgrest  https://postgrest.org/en/stable/auth.html
Postgrest uses JWT to authenticate incoming requests, but the db can authorize db queries based 
on users.


authenticator is passed via db-uri
anon: db-anon-role (PGRST_DB_ANON_ROLE)
jwt-secret (PGRST_JWT_SECRET)


HOW LOGIN WORKS --> {
    take username and password,
    get the role and any other info we want tokenized,
    if login successful --> return json token
}

Generate JWT in SQL ---> pgjwt
https://github.com/michelp/pgjwt
https://app.bountysource.com/issues/89971002-example-code-to-show-how-to-install-pgjwt-extension-in-docker


How to access info on JWT for the current user --> to be user in policy creation::
current_setting('request.jwt.claims', true)::json->>'username';


*/


/* AUTH schema and functions */
DROP SCHEMA IF EXISTS auth CASCADE;
CREATE SCHEMA auth;


/* necesary extenstions */
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pgjwt;

/* an auth user table */
CREATE TABLE IF NOT EXISTS 
auth.users(
  id     serial primary key,
  firstname text not null,
  lastname text not null,
  username  text not null,
  pass   text not null check (length(pass) < 512),
  role   name not null check (length(role) < 512)
);

-- data privilege roles
CREATE TABLE IF NOT EXISTS auth.data_roles(
    id SERIAL PRIMARY KEY,
    role text,
    description text
);
-- default data roles
INSERT INTO auth.data_roles(role, description) VALUES
    ('reader', 'user can only perform SELECT on data'),
    ('writer', 'user can SELECT, INSERT, and UPDATE'),
    ('deleter', 'user can SELECT, INSERT, and UPDATE'),
    ('manager', 'user encompasses privileges of deleter and can manage user permissions on data');

/* Example of a basic data id to role */
CREATE TABLE IF NOT EXISTS
auth.user_projects(
  id serial primary key,
  user_ int REFERENCES auth.users(id),
  project int REFERENCES macrostrat.projects(id),
  role_id integer REFERENCES auth.data_roles(id)
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
auth.user_role(username TEXT, pass TEXT) RETURNS name
  LANGUAGE plpgsql
  AS $$
BEGIN
  RETURN (
  SELECT role FROM auth.users
   WHERE users.username = user_role.username
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
macrostrat_api.login(username text, pass text) RETURNS auth.jwt_token AS $$
DECLARE
    _role name;
    result auth.jwt_token;
BEGIN
    SELECT auth.user_role(username, pass) INTO _role;
    IF _role IS NULL THEN
        raise invalid_password using message = 'invalid user or password';
    END IF;
    -- sign function comes from pgjwt extension. 
    SELECT sign(
            row_to_json(r), 'reallyreallyreallyreallyverysafesafesafesafe'
        ) AS token
        FROM (
            SELECT 'api_user' as role, login.username as username,
            extract(epoch FROM now())::integer + 86400 AS exp --expires in 1 day
        ) r
        INTO result;
    RETURN result;
END
$$ language plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION
macrostrat_api.create_user(firstname text, lastname text, pass text, username text) 
RETURNS BOOLEAN AS $$
DECLARE
  _role name;
BEGIN
  INSERT INTO auth.users(username, firstname, lastname, pass, role) 
    VALUES (username, firstname, lastname, pass, 'api_user');
  SELECT auth.user_role(username, pass) INTO _role;

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
CREATE ROLE authenticator NOINHERIT LOGIN;
GRANT anon TO authenticator;

GRANT USAGE ON SCHEMA macrostrat_api TO anon;
GRANT USAGE ON SCHEMA macrostrat_api TO authenticator;

GRANT EXECUTE ON FUNCTION macrostrat_api.login(text,text) TO anon;
GRANT EXECUTE ON FUNCTION macrostrat_api.create_user(text,text,text, text) TO anon;
GRANT EXECUTE ON FUNCTION macrostrat_api.login(text,text) TO authenticator;
GRANT EXECUTE ON FUNCTION macrostrat_api.create_user(text,text,text, text) TO authenticator;

-- a general api_user, data privileges depend on RLS
GRANT USAGE ON SCHEMA auth TO api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO api_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO api_user;

GRANT api_user to authenticator;

/* ################### Row level policies ################### */


/* function to get username off of jwt claims*/
CREATE OR REPLACE FUNCTION
macrostrat_api.get_username() returns text AS $$
DECLARE
  username_ text;
BEGIN
  SELECT current_setting('request.jwt.claims', true)::json->>'username' INTO username_;
RETURN username_;
END
$$language plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION
auth.user_project_insert() RETURNS trigger AS $$
DECLARE
  username_ text;
  id_ int;
  manager_id int;
BEGIN
  IF tg_op = 'INSERT' THEN
    select macrostrat_api.get_username() into username_;
    select id from auth.users where users.username = username_ INTO id_;
    SELECT id FROM auth.data_roles WHERE role = 'manager' INTO manager_id;
    INSERT INTO auth.user_projects(user_, project, role_id) 
      VALUES(id_, new.id, manager_id);
  END IF;
  RETURN new;
END
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP trigger IF EXISTS user_projects ON macrostrat.projects;
CREATE trigger user_projects
  AFTER INSERT ON macrostrat.projects
  FOR EACH ROW
  EXECUTE PROCEDURE auth.user_project_insert();

CREATE OR REPLACE FUNCTION
macrostrat_api.current_user_projects() 
RETURNS TABLE (project integer, role text) AS $$
DECLARE
  username_ text;
BEGIN
  SELECT macrostrat_api.get_username() INTO username_;
  RETURN QUERY
    SELECT up.project, adr.role FROM auth.user_projects up
    JOIN auth.users u
    on u.id = up.user_
    JOIN auth.data_roles adr
    ON adr.id = up.role_id
    WHERE u.username = username_;
END
$$ language plpgsql SECURITY DEFINER;

/* users table */
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY secure_users ON auth.users 
USING (username = macrostrat_api.get_username())
WITH CHECK (username = macrostrat_api.get_username());

/* user_projects mapping tables */
ALTER TABLE auth.user_projects ENABLE ROW LEVEL SECURITY;

-- Only project managers can view and manipulate project privileges
CREATE POLICY manager_projects ON auth.user_projects
USING (project IN (
    SELECT project from macrostrat_api.current_user_projects() 
    WHERE role = 'manager'))
WITH CHECK (project IN (
    SELECT project from macrostrat_api.current_user_projects() 
    WHERE role = 'manager'));


/* projects */
ALTER TABLE macrostrat.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_ ON macrostrat.projects FOR SELECT
USING (id IN (
  SELECT project FROM macrostrat_api.current_user_projects()  
  WHERE role IN ('reader','writer','deleter','manager')));

-- anyone can insert a new project
CREATE POLICY projects_insert ON macrostrat.projects FOR INSERT
WITH CHECK(TRUE);

-- Updates only allowable for writer, deleter or manager
CREATE POLICY projects_update ON macrostrat.projects FOR UPDATE
USING(id IN (
    SELECT project from macrostrat_api.current_user_projects()
    WHERE role IN ('writer','deleter', 'manager')
))
WITH CHECK (id IN (
    SELECT project from macrostrat_api.current_user_projects()
    WHERE role IN ('writer','deleter', 'manager')
));

/* col-groups */
ALTER TABLE macrostrat.col_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY col_groups_select ON macrostrat.col_groups FOR SELECT
USING (project_id IN (
  SELECT project FROM macrostrat_api.current_user_projects()
  WHERE role IN ('reader','writer','deleter','manager')));


CREATE POLICY col_group_update ON macrostrat.col_groups FOR UPDATE
USING(project_id IN (
  SELECT project FROM macrostrat_api.current_user_projects() 
  WHERE role IN ('writer', 'deleter', 'manager')));

CREATE POLICY col_group_insert ON macrostrat.col_groups FOR INSERT
WITH CHECK(project_id IN (
  SELECT project FROM macrostrat_api.current_user_projects() 
  WHERE role IN ('writer', 'deleter', 'manager')));

/* cols */
ALTER TABLE macrostrat.cols ENABLE ROW LEVEL SECURITY;

CREATE POLICY cols_select ON macrostrat.cols FOR SELECT
USING (project_id IN (SELECT project FROM macrostrat_api.current_user_projects()));

CREATE POLICY cols_update ON macrostrat.cols for UPDATE
USING(project_id IN (
  SELECT project FROM macrostrat_api.current_user_projects()
  WHERE role IN ('writer', 'deleter', 'manager')
));

CREATE POLICY cols_insert ON macrostrat.cols for INSERT
WITH CHECK(project_id IN (
  SELECT project FROM macrostrat_api.current_user_projects()
  WHERE role IN ('writer', 'deleter', 'manager')
));

/* units */
ALTER TABLE macrostrat.units ENABLE ROW LEVEL SECURITY;

CREATE POLICY units_select ON macrostrat.units FOR SELECT
USING (col_id IN (
  SELECT c.id from macrostrat.cols c 
  WHERE c.project_id IN(
    SELECT project FROM macrostrat_api.current_user_projects())));

CREATE POLICY units_update ON macrostrat.units FOR UPDATE
USING (col_id IN (
  SELECT c.id from macrostrat.cols c 
  WHERE c.project_id IN(
    SELECT project FROM macrostrat_api.current_user_projects()
    WHERE role IN ('writer', 'deleter', 'manager'))));
    
CREATE POLICY units_insert ON macrostrat.units FOR INSERT
WITH CHECK (col_id IN (
  SELECT c.id from macrostrat.cols c 
  WHERE c.project_id IN(
    SELECT project FROM macrostrat_api.current_user_projects()
    WHERE role IN ('writer', 'deleter', 'manager'))));

CREATE OR REPLACE VIEW macrostrat_api.users AS
SELECT * FROM auth.users;
ALTER VIEW macrostrat_api.users OWNER TO api_user;

CREATE OR REPLACE VIEW macrostrat_api.user_projects AS
SELECT * FROM auth.user_projects;
ALTER VIEW macrostrat_api.user_projects OWNER TO api_user;

CREATE OR REPLACE VIEW macrostrat_api.data_roles AS
SELECT * FROM auth.data_roles;
ALTER VIEW macrostrat_api.data_roles OWNER TO api_user;

ALTER TABLE auth.data_roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY data_roles_select ON auth.data_roles FOR SELECT
USING(TRUE);

CREATE POLICY data_roles_update ON auth.data_roles FOR UPDATE
USING (role NOT IN('reader','writer','deleter', 'manager'));

CREATE POLICY data_roles_insert ON auth.data_roles FOR INSERT
WITH CHECK(role NOT IN ('reader', 'writer', 'deleter', 'manager'));