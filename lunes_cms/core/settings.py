"""
Django settings for lunes-cms project.

Generated by 'django-admin startproject' using Django 2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

from distutils.util import strtobool

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from .logging_formatter import ColorFormatter

###################
# CUSTOM SETTINGS #
###################

#: Build paths inside the project like this: ``os.path.join(BASE_DIR, ...)``
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: How many documents a training sets needs at least to get released
TRAININGSET_MIN_DOCS = int(os.environ.get("LUNES_CMS_TRAININGSET_MIN_DOCS", 4))


########################
# DJANGO CORE SETTINGS #
########################

#: A boolean that turns on/off debug mode (see :setting:`django:DEBUG`)
#:
#: .. warning::
#:     Never deploy a site into production with :setting:`DEBUG` turned on!
DEBUG = bool(strtobool(os.environ.get("LUNES_CMS_DEBUG", "False")))

#: Enabled applications (see :setting:`django:INSTALLED_APPS`)
INSTALLED_APPS = [
    # Installed custom apps
    "lunes_cms.api",
    "lunes_cms.cms",
    "lunes_cms.help",
    # Django jazzmin needs to be installed before Django admin
    "jazzmin",
    # Installed Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    # Installed third-party-apps
    "drf_spectacular",
    "mptt",
    "pydub",
    "rest_framework",
    "qr_code",
]

#: Activated middlewares (see :setting:`django:MIDDLEWARE`)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

#: Default URL dispatcher (see :setting:`django:ROOT_URLCONF`)
ROOT_URLCONF = "lunes_cms.core.urls"

#: Config for HTML templates (see :setting:`django:TEMPLATES`)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "lunes_cms.core.context_processors.feedback_processor",
            ],
        },
    },
]

#: WSGI (Web Server Gateway Interface) config (see :setting:`django:WSGI_APPLICATION`)
WSGI_APPLICATION = "lunes_cms.core.wsgi.application"

#: The URL or named URL pattern where requests are redirected for login (see :setting:`django:LOGIN_URL`)
LOGIN_URL = "/admin/login/"

#: The URL or named URL pattern where requests are redirected after login when the
#: LoginView doesn't get a next GET parameter. (see :setting:`django:LOGIN_REDIRECT_URL`).
LOGIN_REDIRECT_URL = "/admin/"


############
# DATABASE #
############

#: A dictionary containing the settings for all databases to be used with this Django installation
#: (see :setting:`django:DATABASES`)
DATABASE_CHOICES = {
    "postgres": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("LUNES_CMS_DB_NAME", "lunes"),
        "USER": os.environ.get("LUNES_CMS_DB_USER", "lunes"),
        "PASSWORD": os.environ.get("LUNES_CMS_DB_PASSWORD", "password"),
        "HOST": os.environ.get("LUNES_CMS_DB_HOST", "localhost"),
        "PORT": os.environ.get("LUNES_CMS_DB_PORT", "5432"),
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    },
}

try:
    #: A dictionary containing the settings for all databases to be used with this Django installation
    #: (see :setting:`django:DATABASES`)
    DATABASES = {
        "default": DATABASE_CHOICES[os.environ.get("LUNES_CMS_DB_BACKEND", "postgres")]
    }
except KeyError as e:
    raise ImproperlyConfigured(
        f"The database backend {os.environ.get('LUNES_CMS_DB_BACKEND')!r} is not supported, must be one of {DATABASE_CHOICES.keys()}."
    ) from e

#: Default primary key field type to use for models that don’t have a field with primary_key=True.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


############
# SECURITY #
############

#: This is a security measure to prevent HTTP Host header attacks, which are possible even under many seemingly-safe
#: web server configurations (see :setting:`django:ALLOWED_HOSTS` and :ref:`django:host-headers-virtual-hosting`)
ALLOWED_HOSTS = [".localhost", "127.0.0.1", "[::1]"] + list(
    filter(
        None,
        (x.strip() for x in os.environ.get("LUNES_CMS_ALLOWED_HOSTS", "").splitlines()),
    )
)

#: A list of IP addresses, as strings, that allow the :func:`~django.template.context_processors.debug` context
#: processor to add some variables to the template context.
INTERNAL_IPS = ["localhost", "127.0.0.1"]

#: The secret key for this particular Django installation (see :setting:`django:SECRET_KEY`)
#:
#: .. warning::
#:     Provide a key via the environment variable ``LUNES_CMS_SECRET_KEY`` in production and keep it secret!
SECRET_KEY = os.environ.get("LUNES_CMS_SECRET_KEY", "dummy" if DEBUG else "")

#: The list of validators that are used to check the strength of user's passwords.
#: See Password validation for more details. By default, no validation is performed and all passwords are accepted.
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


########################
# INTERNATIONALIZATION #
########################

#: A list of directories where Django looks for translation files
#: (see :setting:`django:LOCALE_PATHS` and :doc:`django:topics/i18n/index`)
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

#: A string representing the language slug for this installation
#: (see :setting:`django:LANGUAGE_CODE` and :doc:`django:topics/i18n/index`)
LANGUAGE_CODE = "en"

#: A list of all available languages (see :setting:`django:LANGUAGES` and :doc:`django:topics/i18n/index`)
LANGUAGES = [
    ("en", _("English")),
    ("de", _("German")),
]

#: A string representing the time zone for this installation
#: (see :setting:`django:TIME_ZONE` and :doc:`django:topics/i18n/index`)
TIME_ZONE = "UTC"

#: A boolean that specifies whether Django’s translation system should be enabled
#: (see :setting:`django:USE_I18N` and :doc:`django:topics/i18n/index`)
USE_I18N = True

#: A boolean that specifies if localized formatting of data will be enabled by default or not
#: (see :setting:`django:USE_L10N` and :doc:`django:topics/i18n/index`)
USE_L10N = True

#: A boolean that specifies if datetimes will be timezone-aware by default or not
#: (see :setting:`django:USE_TZ` and :doc:`django:topics/i18n/index`)
USE_TZ = True


################
# STATIC FILES #
################

#: This setting defines the additional locations the :mod:`django.contrib.staticfiles` app will traverse to collect
#: static files for deployment or to serve them during development (see :setting:`django:STATICFILES_DIRS` and
#: :doc:`Managing static files <django:howto/static-files/index>`).
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

#: URL to use in development when referring to static files located in :setting:`STATICFILES_DIRS`
#: (see :setting:`django:STATIC_URL` and :doc:`Managing static files <django:howto/static-files/index>`)
STATIC_URL = "/static/"

#: The absolute path to the output directory where :mod:`django.contrib.staticfiles` will put static files for
#: deployment (see :setting:`django:STATIC_ROOT` and :doc:`Managing static files <django:howto/static-files/index>`)
#: In debug mode, this is not required since :mod:`django.contrib.staticfiles` can directly serve these files.
STATIC_ROOT = os.environ.get("LUNES_CMS_STATIC_ROOT")

#: URL that handles the media served from :setting:`MEDIA_ROOT` (see :setting:`django:MEDIA_URL`)
MEDIA_URL = "/media/"

#: Absolute filesystem path to the directory that will hold user-uploaded files (see :setting:`django:MEDIA_ROOT`)
MEDIA_ROOT = os.environ.get("LUNES_CMS_MEDIA_ROOT", os.path.join(BASE_DIR, "media"))


##########
# EMAILS #
##########

if DEBUG:
    #: The backend to use for sending emails (see :setting:`django:EMAIL_BACKEND` and :doc:`django:topics/email`)
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

#: The email address that error messages come from, such as those sent to :setting:`django:ADMINS`.
#: (see :setting:`django:SERVER_EMAIL`)
SERVER_EMAIL = os.environ.get("LUNES_CMS_SERVER_EMAIL", "keineantwort@lunes.app")

#: Default email address to use for various automated correspondence from the site manager(s)
#: (see :setting:`django:DEFAULT_FROM_EMAIL`)
DEFAULT_FROM_EMAIL = SERVER_EMAIL

#: The host to use for sending email (see :setting:`django:EMAIL_HOST`)
EMAIL_HOST = os.environ.get("LUNES_CMS_EMAIL_HOST", "localhost")

#: Password to use for the SMTP server defined in :attr:`~lunes_cms.core.settings.EMAIL_HOST`
#: (see :setting:`django:EMAIL_HOST_PASSWORD`). If empty, Django won’t attempt authentication.
EMAIL_HOST_PASSWORD = os.environ.get("LUNES_CMS_EMAIL_HOST_PASSWORD")

#: Username to use for the SMTP server defined in :attr:`~lunes_cms.core.settings.EMAIL_HOST`
#: (see :setting:`django:EMAIL_HOST_USER`). If empty, Django won’t attempt authentication.
EMAIL_HOST_USER = os.environ.get("LUNES_CMS_EMAIL_HOST_USER", SERVER_EMAIL)

#: Port to use for the SMTP server defined in :attr:`~lunes_cms.core.settings.EMAIL_HOST`
#: (see :setting:`django:EMAIL_PORT`)
EMAIL_PORT = int(os.environ.get("LUNES_CMS_EMAIL_PORT", 587))

#: Whether to use a TLS (secure) connection when talking to the SMTP server.
#: This is used for explicit TLS connections, generally on port 587.
#: (see :setting:`django:EMAIL_USE_TLS`)
EMAIL_USE_TLS = bool(strtobool(os.environ.get("LUNES_CMS_EMAIL_USE_TLS", "True")))

#: Whether to use an implicit TLS (secure) connection when talking to the SMTP server.
#: In most email documentation this type of TLS connection is referred to as SSL. It is generally used on port 465.
#: (see :setting:`django:EMAIL_USE_SSL`)
EMAIL_USE_SSL = bool(strtobool(os.environ.get("LUNES_CMS_EMAIL_USE_SSL", "False")))


###########
# LOGGING #
###########

#: The log level for lunes-cms django apps
LOG_LEVEL = os.environ.get("LUNES_CMS_LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

#: The log level for the syslog
SYS_LOG_LEVEL = "INFO"

#: The log level for dependencies
DEPS_LOG_LEVEL = os.environ.get("LUNES_CMS_DEPS_LOG_LEVEL", "INFO" if DEBUG else "WARN")

#: The file path of the logfile. Needs to be writable by the application.
LOGFILE = os.environ.get("LUNES_CMS_LOGFILE", os.path.join(BASE_DIR, "lunes-cms.log"))

#: Logging configuration dictionary (see :setting:`django:LOGGING`)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{asctime} \x1b[1m{levelname}\x1b[0m {name} - {message}",
            "datefmt": "%b %d %H:%M:%S",
            "style": "{",
        },
        "console-colored": {
            "()": ColorFormatter,
            "format": "{asctime} {levelname} {name} - {message}",
            "datefmt": "%b %d %H:%M:%S",
            "style": "{",
        },
        "logfile": {
            "format": "{asctime} {levelname:7} {name} - {message}",
            "datefmt": "%b %d %H:%M:%S",
            "style": "{",
        },
        "syslog": {
            "format": "LUNES CMS - {levelname}: {message}",
            "style": "{",
        },
        "email": {
            "format": "Date and time: {asctime}\nSeverity: {levelname}\nLogger: {name}\nMessage: {message}\nFile: {funcName}() in {pathname}:{lineno}",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "console-colored": {
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "console-colored",
        },
        "logfile": {
            "class": "logging.FileHandler",
            "filename": LOGFILE,
            "formatter": "logfile",
        },
        "authlog": {
            "filters": ["require_debug_false"],
            "class": "logging.handlers.SysLogHandler",
            "address": "/dev/log",
            "facility": "auth",
            "formatter": "syslog",
        },
        "syslog": {
            "filters": ["require_debug_false"],
            "class": "logging.handlers.SysLogHandler",
            "address": "/dev/log",
            "facility": "syslog",
        },
    },
    "loggers": {
        # Loggers of lunes-cms django apps
        "lunes_cms": {
            "handlers": ["console-colored", "logfile"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Syslog for authentication
        "auth": {
            "handlers": ["console", "logfile", "authlog", "syslog"],
            "level": SYS_LOG_LEVEL,
            "propagate": False,
        },
        # Loggers of dependencies
        "django": {
            "handlers": ["console", "logfile"],
            "level": DEPS_LOG_LEVEL,
            "propagate": False,
        },
        "": {
            "handlers": ["console", "logfile"],
            "level": DEPS_LOG_LEVEL,
            "propagate": True,
        },
    },
}


#########################
# DJANGO REST FRAMEWORK #
#########################

#: Configuration of Django REST Framework
REST_FRAMEWORK = {
    # "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "ALLOWED_VERSIONS": ("v1", "v2"),
    "DEFAULT_VERSION": "default",
    "DEFAULT_API_URL": "http://localhost:8080/api/",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Lunes API",
    "DESCRIPTION": "The API documentation for the Lunes CMS",
    "VERSION": None,
    "SCHEMA_PATH_PREFIX": "/api(/v[0-9])?",
    "CONTACT": {"email": "tech@integreat-app.de"},
    "LICENSE": {
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    "SWAGGER_UI_FAVICON_HREF": "/favicon.ico",
    "SWAGGER_UI_SETTINGS": """{
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
    }""",
}

##################
# DJANGO JAZZMIN #
##################

#: Basic settings for Django Jazzmin
JAZZMIN_SETTINGS = {
    "site_brand": _("Lunes Administration"),
    "site_title": _("Lunes Administration"),
    "welcome_sign": _("Welcome to the vocabulary management of Lunes!"),
    "site_header": _("Lunes Administration"),
    "site_logo": "images/logo.svg",
    "site_icon": "images/logo.svg",
    "login_logo": "images/logo-lunes.svg",
    "login_logo_dark": "images/logo-lunes-dark.svg",
    "site_logo_classes": "",
    "changeform_format": "collapsible",
    "language_chooser": True,
    "custom_css": "css/corporate_identity.css",
    "custom_js": "js/corporate_identity.js",
    "icons": {
        "auth.user": "fas fa-user-edit",
        "auth.Group": "fas fa-users",
        "cms.Discipline": "fas fa-book",
        "cms.TrainingSet": "fas fa-stream",
        "cms.Document": "fab fa-amilia",
        "cms.GroupAPIKey": "fas fa-key",
        "cms.Feedback": "fas fa-comment",
        "cms.Sponsor": "fas fa-star",
    },
}

#: UI tweaks for Django Jazzmin
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-navy",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-primary navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": True,
    "sidebar_nav_flat_style": False,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}


############
# QR CODES #
############

SERVE_QR_CODE_IMAGE_PATH = ""
