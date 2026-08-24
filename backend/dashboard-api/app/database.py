from open_hoops.core.database import Database

from app.config import settings

database = Database(settings.database_url)
