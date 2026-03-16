"""Shared room-scan copy used by both demo and regular mode."""

from __future__ import annotations

ROOM_SCAN_PROMPT: str = (
    "Good. First hold the camera still so I can confirm the feed. "
    "If the image is black, dark, blurry, or unstable, fix that before you move. "
    "Once the feed is clear, step to a corner or doorway and show me the widest view of the room in one steady shot. "
    "Hold that framing for a few seconds. Keep the doorway, mirrors, sinks, tables, and lights in frame when you can. "
    "If a blind spot or work surface matters later and I cannot see it, I will stop you and ask for that area specifically. "
    "I will tell you when I have enough of the room."
)
