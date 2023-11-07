"""
Authentication based on username/password and cookies.
"""

from fastapi import APIRouter

router = APIRouter(prefix="auth", tags=["auth"])
