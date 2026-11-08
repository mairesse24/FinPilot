"""Run project commands with python -m scripts.<command> from repository root."""
from pkgutil import extend_path

# The backend MVP also has scripts/seed_database.py. Keep both command sets
# discoverable when the repository root and backend are on Python's path.
__path__ = extend_path(__path__, __name__)
