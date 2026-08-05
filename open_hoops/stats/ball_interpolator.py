from __future__ import annotations


def interpolate_ball(
    positions: list[tuple[float, float] | None],
    fps: float,
    max_gap_sec: float = 0.5,
) -> list[tuple[float, float] | None]:
    """Fill short gaps in ball positions with linear interpolation.

    Gaps longer than max_gap_sec are left as None.
    Gaps at start/end (no anchor on one side) are left as None.
    """
    if not positions:
        return []

    max_gap_frames = int(max_gap_sec * fps)
    result: list[tuple[float, float] | None] = list(positions)

    i = 0
    while i < len(result):
        if result[i] is not None:
            i += 1
            continue

        # Find gap boundaries
        gap_start = i
        while i < len(result) and result[i] is None:
            i += 1
        gap_end = i  # first non-None after gap (or len)

        # Need anchors on both sides
        if gap_start == 0 or gap_end >= len(result):
            continue

        gap_len = gap_end - gap_start
        if gap_len > max_gap_frames:
            continue

        # Linear interpolation
        before = result[gap_start - 1]
        after = result[gap_end]
        for j in range(gap_len):
            t = (j + 1) / (gap_len + 1)
            result[gap_start + j] = (
                before[0] + t * (after[0] - before[0]),
                before[1] + t * (after[1] - before[1]),
            )

    return result
