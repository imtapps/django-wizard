# rules lives in a directory above our example
# app so we need to make sure it is findable on our path.
import sys
from os.path import abspath, dirname, join
parent = abspath(dirname(__file__))
grandparent = abspath(join(parent, '..'))
for path in (grandparent, parent):
    if path not in sys.path:
        sys.path.insert(0, path)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example.db',
    }
}

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = ('127.0.0.1',)

STATIC_URL = '/static/'

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    abspath(join(parent, 'templates')),
)

DEBUG_TOOLBAR_CONFIG = {
#    'INTERCEPT_REDIRECTS':False
    'EXTRA_SIGNALS':[
        'wizard.signals.wizard_pre_save',
        'wizard.signals.wizard_post_save',
    ]
}
INSTALLED_APPS = (
    'wizard',
    'sample',
    'debug_toolbar',
)

