INSERT INTO auth.users(email, pass) VALUES 
    ('fake_man@fake.com', 'fakepassword');
    
INSERT INTO auth.user_projects(user_, project, privilege) VALUES
    (1, 1, 'owner');