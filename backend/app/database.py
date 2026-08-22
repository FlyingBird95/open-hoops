from app.config import settings
from open_hoops.core.database import Database

database = Database(settings.database_url)
