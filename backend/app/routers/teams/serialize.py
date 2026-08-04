from app.models import Team
from app.jsonapi import resource_object


def serialize_team(team: Team) -> dict:
    return resource_object(
        type="teams",
        uid=team.uid,
        attributes={
            "name": team.name,
            "is_own": team.is_own,
            "home_color": team.home_color,
            "away_color": team.away_color,
        },
    )
