"""
API dependencies — re-exports from FastAPI-Users for convenience.
"""

from app.core.auth import current_active_user, current_superuser

get_current_active_user = current_active_user
get_current_superuser = current_superuser
