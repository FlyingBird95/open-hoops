from app.models import Player
from app.jsonapi import resource_object, relationship_linkage


def serialize_player(player: Player) -> dict:
    return resource_object(
        type="players",
        uid=player.uid,
        attributes={
            "jersey_number": player.jersey_number,
            "name": player.name,
        },
        relationships={
            "team": relationship_linkage("teams", player.team.uid),
        },
    )
