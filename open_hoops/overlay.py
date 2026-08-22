import cv2
import numpy as np


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (255, 255, 255)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return b, g, r


class Overlay:
    HUD_H = 60
    HUD_W = 400
    MARGIN = 10

    def render(
        self,
        frame: np.ndarray,
        scores: dict[str, int],
        team_colors: dict[str, str],
        frame_idx: int,
        fps: float,
    ) -> np.ndarray:
        out = frame.copy()
        _h, w = out.shape[:2]

        # background strip
        x0 = (w - self.HUD_W) // 2
        y0 = self.MARGIN
        x1, y1 = x0 + self.HUD_W, y0 + self.HUD_H
        cv2.rectangle(out, (x0, y0), (x1, y1), (20, 20, 20), -1)
        cv2.rectangle(out, (x0, y0), (x1, y1), (200, 200, 200), 2)

        score_a = scores.get("team_a", 0)
        score_b = scores.get("team_b", 0)
        color_a = _hex_to_bgr(team_colors.get("team_a", "#ffffff"))
        color_b = _hex_to_bgr(team_colors.get("team_b", "#ffffff"))

        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"{score_a}  -  {score_b}"
        (tw, th), _ = cv2.getTextSize(text, font, 1.2, 2)
        tx = x0 + (self.HUD_W - tw) // 2
        ty = y0 + self.HUD_H // 2 + th // 2

        half = self.HUD_W // 2
        cv2.rectangle(out, (x0, y0 + 2), (x0 + half, y1 - 2), color_a, -1)
        cv2.rectangle(out, (x0 + half, y0 + 2), (x1, y1 - 2), color_b, -1)
        cv2.putText(out, text, (tx, ty), font, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

        elapsed = int(frame_idx / fps) if fps > 0 else 0
        mins, secs = divmod(elapsed, 60)
        clock = f"{mins:02d}:{secs:02d}"
        cv2.putText(out, clock, (x1 + 10, ty), font, 0.7, (220, 220, 220), 1, cv2.LINE_AA)

        return out
