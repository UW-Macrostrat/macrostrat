import os

# Importing the app builds the sign-in routes, which need these set.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIRECT_URI", "http://localhost:8000/security/callback")
