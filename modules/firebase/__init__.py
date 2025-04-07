# Remove the circular import
# from modules.database.service import DatabaseService

# Keep other necessary imports
from .config import db
from .user_management import UserManager

__all__ = ['UserManager', 'db'] 