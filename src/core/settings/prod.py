import warnings

from .base import *  
DEBUG = False

if not ALLOWED_HOSTS:
    warnings.warn(
        "DJANGO_ALLOWED_HOSTS is not set — falling back to '*'. "
        "Set it explicitly once the deployment platform supports custom env vars.",
        RuntimeWarning,
    )
    ALLOWED_HOSTS = ["*"]