from open_hoops.service.event.models import GameEvent

from app.jsonapi import relationship_linkage, resource_object


def serialize_event(ev: GameEvent) -> dict:
    rels: dict = {"game": relationship_linkage("games", ev.game.uid)}
    if ev.team:
        rels["team"] = relationship_linkage("teams", ev.team.uid)
    if ev.player:
        rels["player"] = relationship_linkage("players", ev.player.uid)
    if ev.player2:
        rels["player2"] = relationship_linkage("players", ev.player2.uid)

    bbox = None
    if ev.bbox_x1 is not None:
        bbox = {"x1": ev.bbox_x1, "y1": ev.bbox_y1, "x2": ev.bbox_x2, "y2": ev.bbox_y2}

    return resource_object(
        type="game_events",
        uid=ev.uid,
        attributes={
            "type": ev.type,
            "frame": ev.frame,
            "timestamp_sec": ev.timestamp_sec,
            "bbox": bbox,
            "source": ev.source.value if ev.source else "analysis",
        },
        relationships=rels,
    )
