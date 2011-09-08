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

STATIC_URL = '/static/'

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    abspath(join(parent, 'templates')),
)

PROJECT_APPS = ('wizard', 'sample')

INSTALLED_APPS = (
    'django_jenkins',
) + PROJECT_APPS

