"""
Gunicorn config for MyRecoveryPal.

Only purpose right now: close database connections after fork when
running with --preload. Without this hook, the master process opens
Postgres connections during start.sh migrate + Django app import, and
every forked worker inherits the same TCP socket. Two workers writing
to one connection → "InterfaceError: connection already closed" on
whichever worker loses the race (Sentry reports hundreds of these).
"""


def post_fork(server, worker):
    from django.db import connections
    for conn in connections.all():
        try:
            conn.close()
        except Exception:
            pass
        # Also null out the underlying DB-API connection so Django
        # definitely opens a fresh one on the first query in this worker.
        if getattr(conn, "connection", None) is not None:
            try:
                conn.connection.close()
            except Exception:
                pass
            conn.connection = None
