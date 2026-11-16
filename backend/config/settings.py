"""
Django settings for config project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    import environ
    env = environ.Env(
        DEBUG=(bool, True),
    )
    environ.Env.read_env(BASE_DIR / ".env")
except ImportError:
    class DummyEnv:
        def __call__(self, key, default=None):
            return os.environ.get(key, default)

        def bool(self, key, default=True):
            val = str(os.environ.get(key, default)).lower()
            return val in ("true", "1", "yes")

    env = DummyEnv()

SECRET_KEY = env("SECRET_KEY", default="django-insecure-asq#^(pcu1gu+q3ph10^7#0=8oif#43q1l2(orn41p4@x$n_xe")
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "requests_app.apps.RequestsAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database Configuration (Lab Session 3)
# Attempts to load MySQLdb / pymysql if available; otherwise falls back to sqlite3 for development.
has_mysql = False
try:
    import MySQLdb  # noqa: F401
    has_mysql = True
except ImportError:
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
        has_mysql = True
    except ImportError:
        has_mysql = False

default_engine = "django.db.backends.mysql" if has_mysql else "django.db.backends.sqlite3"
db_engine = env("DB_ENGINE", default=default_engine)

if "sqlite" in db_engine or not has_mysql:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": db_engine,
            "NAME": env("DB_NAME", default="sen305_servicedesk"),
            "USER": env("DB_USER", default="sen305_app"),
            "PASSWORD": env("DB_PASSWORD", default="P@55w0rd!"),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }

# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication redirects (Lab Session 4)
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "requests:list"
LOGOUT_REDIRECT_URL = "core:home"

# Email
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
