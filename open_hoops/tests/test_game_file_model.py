from open_hoops.db import GameFile, generate_uid


def test_game_file_has_required_columns():
    gf = GameFile(
        uid=generate_uid(),
        game_id=1,
        file_path="uploads/abc.mp4",
        position=0,
        original_filename="game_part1.mp4",
        size_bytes=1024000,
    )
    assert gf.file_path == "uploads/abc.mp4"
    assert gf.position == 0
    assert gf.original_filename == "game_part1.mp4"
    assert gf.size_bytes == 1024000
