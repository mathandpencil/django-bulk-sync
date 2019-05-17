import os
import dj_database_url

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), os.pardir)

SECRET_KEY = 'testsecretkey43u2894u329h432nuhrn32iu'
DEBUG = True

db_url = os.environ.get("DATABASE_URL", "sqlite://localhost/:memory:")
DB = dj_database_url.parse(db_url)

DATABASES = {
    'default': DB,
}

INSTALLED_APPS = ('bulk_sync', 'tests',)
MIDDLEWARE_CLASSES = ()
