# coding: utf-8
# db_outage/views.py

"""Default view to display outage message when the database is inaccessible."""


from __future__ import unicode_literals

import logging
import sys
import traceback

import cx_Oracle

from StringIO import StringIO

from django.conf import settings
from django.core.mail import mail_admins
from django.db import connections
from django.db.utils import DatabaseError as django_DatabaseError

from db_outage.views import DBOutage


__author__ = 'David Voegtle (dvoegtle@austin.utexas.edu)'


logger = logging.getLogger('django')

_using_manage = True in ['manage.py' in arg for arg in sys.argv]

TESTING = ((_using_manage and 'test' in sys.argv) or ('nosetests' in sys.argv))


def get_printable_traceback():
    """Return a readable string representation of a traceback.

    Because of how Python (2) represents exceptions, this function must be called
    _while_ an exception is being handled (i.e. in a try/except block).
    """
    exctype, exc, trace = sys.exc_info()
    if not trace:
        return None
    msg = StringIO()
    traceback.print_tb(trace, file=msg)
    del trace
    msg.seek(0)
    return msg.read()


class DBOutageMiddleware(object):
    """Wrap requests with function that tests for database availability."""

    def process_request(self, request):
        """Ping database, and if down log message and return standard outage view."""
        if settings.STATIC_URL in request.path:
            return None

        # Django tests may set their own ROOT_URLCONF, in which case we may not
        # be able to resolve 'shutdown', so we'll just return None unless
        # testing this app intentionally.
        if TESTING and set(['db_outage', 'test_db_outage']).isdisjoint(sys.argv):
            return None

        try:
            self._ping_db()
        except (django_DatabaseError, cx_Oracle.DatabaseError) as exc:
            msg = '\n'.join([
                'Your application is having trouble connecting to the database. Please investigate.',
                get_printable_traceback(),
                str(exc)
            ])
            mail_admins('DatabaseError', msg, fail_silently=True)
            logger.error(msg)
            return DBOutage.as_view()(request)

        return None

    def _ping_db(self, db='default'):
        with connections[db].cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUAL")
        return None
