from app.jsonapi import relationship_linkage, resource_object
from open_hoops.service.player.models import Player


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
