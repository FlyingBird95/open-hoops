from open_hoops.core.database import Database
from open_hoops.service.game.models import GameLog, LogLevel


class GameLogger:
    def __init__(self, database: Database, game_id: int):
        self.database = database
        self.game_id = game_id

    def info(self, message: str, *args, **kwargs) -> None:
        with self.database.use_scoped_session() as session:
            session.add(
                GameLog(
                    game_id=self.game_id,
                    level=LogLevel.info,
                    message=message % args if args else message,
                )
            )

    def warning(self, message: str, *args, **kwargs) -> None:
        with self.database.use_scoped_session() as session:
            session.add(
                GameLog(
                    game_id=self.game_id,
                    level=LogLevel.warning,
                    message=message % args if args else message,
                )
            )

    def error(self, message: str, *args, **kwargs) -> None:
        with self.database.use_scoped_session() as session:
            session.add(
                GameLog(
                    game_id=self.game_id,
                    level=LogLevel.error,
                    message=message % args if args else message,
                )
            )
