"""Canonical curated task library for Prompt 15 backend planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

TaskId: TypeAlias = Literal[
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
    "T7",
    "T8",
    "T9",
    "T10",
    "T11",
    "T12",
    "T13",
    "T14",
    "T15",
]
TaskTier: TypeAlias = Literal[1, 2, 3]
TaskRoleCategory: TypeAlias = Literal["containment", "diagnostic", "flavor"]
TaskStoryFunction: TypeAlias = Literal[
    "boundary",
    "visibility",
    "stabilization",
    "anchor",
    "mark",
    "reflection",
    "diagnosis",
    "seal",
    "fallback",
]
TaskVerificationClass: TypeAlias = Literal[
    "strict_visual",
    "soft_visual",
    "self_report",
]

_EXPECTED_TASK_IDS: Final[tuple[TaskId, ...]] = (
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
    "T7",
    "T8",
    "T9",
    "T10",
    "T11",
    "T12",
    "T13",
    "T14",
    "T15",
)
_ALLOWED_TIERS: Final[frozenset[int]] = frozenset({1, 2, 3})
_ALLOWED_ROLE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"containment", "diagnostic", "flavor"}
)
_ALLOWED_STORY_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        "boundary",
        "visibility",
        "stabilization",
        "anchor",
        "mark",
        "reflection",
        "diagnosis",
        "seal",
        "fallback",
    }
)
_ALLOWED_VERIFICATION_CLASSES: Final[frozenset[str]] = frozenset(
    {"strict_visual", "soft_visual", "self_report"}
)


@dataclass(frozen=True)
class TaskDefinition:
    id: TaskId
    name: str
    tier: TaskTier
    role_category: TaskRoleCategory
    story_function: TaskStoryFunction
    operator_description: str
    verification_class: TaskVerificationClass
    substitution_group: str
    can_block_progression: bool
    # -- Per-task verification profile --
    baseline_prompt: str | None = None
    baseline_lore: str | None = None
    target_object: str | None = None
    completion_check: str | None = None


TASK_LIBRARY: Final[tuple[TaskDefinition, ...]] = (
    # Boundary opener that gets the room edge on screen and establishes that
    # the hotline is working with a defined containment perimeter.
    TaskDefinition(
        id="T1",
        name="Show Threshold",
        tier=1,
        role_category="containment",
        story_function="boundary",
        operator_description=(
            "Ask the caller to show the doorway, threshold, or room edge that "
            "defines the working boundary."
        ),
        verification_class="strict_visual",
        substitution_group="boundary_control",
        can_block_progression=True,
        baseline_prompt=(
            "Point the camera at your doorway — quickly. I need to see the "
            "full frame, threshold to threshold."
        ),
        baseline_lore=(
            "These things feed on transitional spaces. Doorways, hallways, "
            "the edges where one room bleeds into another. Last caller I had, "
            "said something was standing just past the frame — right where "
            "the hallway light didn't quite reach."
        ),
        target_object="doorway or room edge",
        completion_check=(
            "The doorway or room boundary should be clearly visible and "
            "defined in frame."
        ),
    ),
    # Strong boundary step that turns the opener into an active containment
    # move by closing or defining the edge of the room.
    TaskDefinition(
        id="T2",
        name="Close Boundary",
        tier=1,
        role_category="containment",
        story_function="seal",
        operator_description=(
            "Have the caller close the door or define the boundary edge so the "
            "room feels contained."
        ),
        verification_class="strict_visual",
        substitution_group="boundary_control",
        can_block_progression=True,
        baseline_prompt=(
            "Show me the door as it is right now — open, right? I need to "
            "see it before you close it."
        ),
        baseline_lore=(
            "An open door is an invitation. You hear that? That low hum? "
            "That's displacement pressure building on the other side. Shut "
            "it. Shut it now. And whatever you do, do NOT look through the "
            "crack as it closes."
        ),
        target_object="open door",
        completion_check=(
            "The door that was previously open should now be visibly closed. "
            "Compare the frames — if the door is still open, the task is NOT done."
        ),
    ),
    # Visibility gate that improves every later camera-aware step without
    # pretending the system can reason from poor lighting.
    TaskDefinition(
        id="T3",
        name="Increase Illumination",
        tier=1,
        role_category="containment",
        story_function="visibility",
        operator_description=(
            "Raise room light with a lamp or switch so the operator can read the "
            "scene honestly."
        ),
        verification_class="strict_visual",
        substitution_group="visibility_control",
        can_block_progression=True,
        baseline_prompt=(
            "Hold the camera steady. Let me see the current light level "
            "in the room — don't move."
        ),
        baseline_lore=(
            "Low light is where they operate. You can't see them but they "
            "can see you. Every shadow in that room right now is a blind spot "
            "for us and a hiding place for whatever is in there with you. "
            "Turn on every light you can reach. Now."
        ),
        target_object="room scene",
        completion_check=(
            "The room should be VISIBLY brighter than the baseline frame. "
            "Compare overall exposure and brightness. If the scene looks the same "
            "darkness level, the lights were NOT turned on."
        ),
    ),
    # Stability gate that makes the camera preview useful before verification
    # windows or diagnosis beats rely on the room feed.
    TaskDefinition(
        id="T4",
        name="Stabilize Camera",
        tier=1,
        role_category="containment",
        story_function="stabilization",
        operator_description=(
            "Hold the phone still against a stable surface or with both hands so "
            "the room feed settles."
        ),
        verification_class="strict_visual",
        substitution_group="stability_control",
        can_block_progression=True,
        baseline_prompt=(
            "I'm getting motion blur on my end. Hold the camera dead "
            "still — rest it against something solid."
        ),
        baseline_lore=(
            "I need a clean read. The displacement pattern looks "
            "like it's oscillating, but I can't tell if that's the "
            "disturbance or your hands shaking. Brace it. Give me a "
            "rock-solid feed."
        ),
        target_object="stable frame",
        completion_check=(
            "The camera feed should be noticeably steadier — less blur, "
            "consistent framing between consecutive frames."
        ),
    ),
    # Anchor step that introduces a clean physical reference point the hotline
    # can reuse for later marks or object placement.
    TaskDefinition(
        id="T5",
        name="Place Paper on Flat Surface",
        tier=1,
        role_category="containment",
        story_function="anchor",
        operator_description=(
            "Place a sheet of paper on a cleared flat surface to create a simple "
            "anchor point."
        ),
        verification_class="strict_visual",
        substitution_group="surface_anchor",
        can_block_progression=True,
        baseline_prompt=(
            "Show me a flat surface — table, desk, whatever you have. "
            "I need to see it empty first."
        ),
        baseline_lore=(
            "We're setting an anchor. Entities displace physical space — "
            "if something moves that paper when you're not looking, we know "
            "the displacement field is active in that zone. Think of it as "
            "a tripwire. Get the paper on there."
        ),
        target_object="flat surface or table",
        completion_check=(
            "A sheet of paper should now be visible on the flat surface that "
            "was shown in the baseline. If the surface still looks empty, "
            "the paper was NOT placed."
        ),
    ),
    # Companion anchor step that clears staging space when paper placement or
    # marking steps need a reliable tabletop area.
    TaskDefinition(
        id="T6",
        name="Clear Small Surface",
        tier=1,
        role_category="containment",
        story_function="anchor",
        operator_description=(
            "Clear a dinner-plate-sized area so later anchor or mark steps have a "
            "clean staging zone."
        ),
        verification_class="strict_visual",
        substitution_group="surface_anchor",
        can_block_progression=True,
        baseline_prompt=(
            "Show me the surface you're going to use. I need to see "
            "what's on it right now."
        ),
        baseline_lore=(
            "Clutter disrupts containment geometry. Every object in that "
            "zone is a potential conduit. Clear it. I've seen setups where "
            "a single cup in the wrong spot broke an entire containment ring."
        ),
        target_object="cluttered surface area",
        completion_check=(
            "The surface that had objects on it in the baseline should now be "
            "visibly cleared — a clean open area where items were before."
        ),
    ),
    # Spoken seal that keeps the hotline voice-first and gives the operator a
    # ritualized line to confirm in the live call.
    TaskDefinition(
        id="T7",
        name="Speak Containment Phrase",
        tier=1,
        role_category="containment",
        story_function="seal",
        operator_description=(
            "Have the caller speak the containment phrase clearly so the operator "
            "can hear the seal step happen live."
        ),
        verification_class="self_report",
        substitution_group="sealing_ritual",
        can_block_progression=True,
        # Self-report — no visual baseline needed
        baseline_prompt=None,
        baseline_lore=None,
        target_object=None,
        completion_check=None,
    ),
    # Ritual marking step that adds hotline texture without pretending every
    # drawn symbol is visually robust enough for hard gating.
    TaskDefinition(
        id="T8",
        name="Draw Simple Mark",
        tier=2,
        role_category="containment",
        story_function="mark",
        operator_description=(
            "Draw a simple containment mark on paper or a card and hold it steady "
            "for inspection."
        ),
        verification_class="soft_visual",
        substitution_group="marking_ritual",
        can_block_progression=False,
        baseline_prompt=(
            "Hold up the paper or card — blank side toward me. Let me "
            "see it clean first."
        ),
        baseline_lore=(
            "Containment marks aren't symbols — they're interruptions. You're "
            "breaking the surface the entity uses to project itself. Any mark "
            "works. An X, a circle, your initials — doesn't matter. What "
            "matters is that YOU put it there. Make it deliberate."
        ),
        target_object="blank paper or card",
        completion_check=(
            "The paper or card should now show a drawn mark that wasn't there in "
            "the baseline. The paper was blank before — it should have visible "
            "ink or pencil marks now."
        ),
    ),
    # Reflection beat that supports room diagnosis and visual flavor when the
    # scene needs another controlled way to inspect surfaces.
    TaskDefinition(
        id="T9",
        name="Show Reflective Surface",
        tier=2,
        role_category="diagnostic",
        story_function="reflection",
        operator_description=(
            "Bring a mirror, dark spoon, or phone screen into view for a brief "
            "reflective check."
        ),
        verification_class="soft_visual",
        substitution_group="visibility_control",
        can_block_progression=False,
        baseline_prompt=(
            "Grab a mirror — any reflective surface. Phone screen face-up "
            "works. Hold it toward the camera."
        ),
        baseline_lore=(
            "Reflections are how they watch you back. You ever catch a mirror "
            "doing something your body didn't? A half-second delay, a shadow "
            "that moved wrong? That's not your imagination — that's displacement "
            "bleed. Hold it steady. Let me look."
        ),
        target_object="mirror or reflective surface",
        completion_check=(
            "A reflective surface should be clearly visible and held toward "
            "the camera for inspection."
        ),
    ),
    # Visibility support beat that gives the operator a high-contrast object to
    # compare against the room feed during uncertain reads.
    TaskDefinition(
        id="T10",
        name="Hold Up Vivid Object",
        tier=2,
        role_category="diagnostic",
        story_function="visibility",
        operator_description=(
            "Hold a bright object in frame so the operator can compare color "
            "stability and exposure."
        ),
        verification_class="soft_visual",
        substitution_group="visibility_control",
        can_block_progression=False,
        baseline_prompt=(
            "Show me your hands — empty, palms up. I'm checking the "
            "feed calibration."
        ),
        baseline_lore=(
            "Color shift is the first sign of active displacement. If that red "
            "looks orange on my end, or that blue goes grey — we've got a field "
            "distortion. Hold something bright and vivid in front of the camera. "
            "I need to compare."
        ),
        target_object="hands or empty area",
        completion_check=(
            "A bright, vivid, colorful object should now be visible in frame "
            "where there wasn't one before."
        ),
    ),
    # Optional release-style seal step that keeps the hotline feeling adaptive
    # when a sink, cup, or water source is nearby.
    TaskDefinition(
        id="T11",
        name="Water Sink Release",
        tier=2,
        role_category="containment",
        story_function="seal",
        operator_description=(
            "If a sink or cup is nearby, run or pour a small amount of water as a "
            "controlled release step."
        ),
        verification_class="soft_visual",
        substitution_group="sealing_ritual",
        can_block_progression=False,
        baseline_prompt=(
            "Is there a sink near you? A cup of water? Show me what "
            "you have access to."
        ),
        baseline_lore=(
            "Running water disrupts the resonance pattern. It's not spiritual — "
            "it's physics. The displacement field can't maintain coherence near "
            "flowing water. Even a trickle breaks it up. Turn it on."
        ),
        target_object="sink or cup or water source",
        completion_check=(
            "Water should be visibly running from the tap, or being poured "
            "from a cup. Look for motion of water compared to the dry baseline."
        ),
    ),
    # Optional marking variant that can swap in when the caller has salt but no
    # paper or prefers a simpler ritual boundary move.
    TaskDefinition(
        id="T12",
        name="Salt Line",
        tier=2,
        role_category="containment",
        story_function="mark",
        operator_description=(
            "If salt is available, place a short line or small pile near the "
            "boundary as a visible mark."
        ),
        verification_class="soft_visual",
        substitution_group="marking_ritual",
        can_block_progression=False,
        baseline_prompt=(
            "Show me the floor near the boundary. The edge of the room, "
            "near the door."
        ),
        baseline_lore=(
            "Salt has been used as a containment boundary for longer than "
            "this hotline has existed. It's not superstition — crystalline "
            "structures scatter the displacement wavefront. Lay a line. "
            "Even a small pile works."
        ),
        target_object="floor near boundary",
        completion_check=(
            "Salt should be visible on the floor near the boundary — a white "
            "line or pile that wasn't there in the baseline frame."
        ),
    ),
    # Pacing fallback that keeps the operator alive between harder tasks and can
    # settle the call when the room or caller needs a controlled pause.
    TaskDefinition(
        id="T13",
        name="Count Backward",
        tier=3,
        role_category="flavor",
        story_function="fallback",
        operator_description=(
            "Count backward slowly to settle the call and create pacing while the "
            "operator reassesses the next move."
        ),
        verification_class="self_report",
        substitution_group="pacing_fallback",
        can_block_progression=False,
        baseline_prompt=None,
        baseline_lore=None,
        target_object=None,
        completion_check=None,
    ),
    # Diagnosis prompt that keeps the hotline conversational and records what
    # the caller actually experienced without inventing new ritual steps.
    TaskDefinition(
        id="T14",
        name="Describe the Sound",
        tier=3,
        role_category="diagnostic",
        story_function="diagnosis",
        operator_description=(
            "Ask what the sound resembled so diagnosis stays alive between major "
            "containment steps."
        ),
        verification_class="self_report",
        substitution_group="diagnostic_probe",
        can_block_progression=False,
        baseline_prompt=None,
        baseline_lore=None,
        target_object=None,
        completion_check=None,
    ),
    # Companion diagnosis prompt that localizes the disturbance and helps later
    # path selection stay grounded in what the caller reported.
    TaskDefinition(
        id="T15",
        name="Answer Where It Was Strongest",
        tier=3,
        role_category="diagnostic",
        story_function="diagnosis",
        operator_description=(
            "Ask where the activity felt strongest in the room to guide the next "
            "task choice."
        ),
        verification_class="self_report",
        substitution_group="diagnostic_probe",
        can_block_progression=False,
        baseline_prompt=None,
        baseline_lore=None,
        target_object=None,
        completion_check=None,
    ),
)


def _validate_task_library() -> None:
    if len(TASK_LIBRARY) != 15:
        raise ValueError("TASK_LIBRARY must contain exactly 15 canonical tasks.")

    task_ids = tuple(task.id for task in TASK_LIBRARY)
    if task_ids != _EXPECTED_TASK_IDS:
        raise ValueError("TASK_LIBRARY IDs must match T1 through T15 in canonical order.")

    if len(set(task_ids)) != len(task_ids):
        raise ValueError("TASK_LIBRARY IDs must be unique.")

    for task in TASK_LIBRARY:
        if task.tier not in _ALLOWED_TIERS:
            raise ValueError(f"Unsupported task tier for {task.id}: {task.tier}")
        if task.role_category not in _ALLOWED_ROLE_CATEGORIES:
            raise ValueError(
                f"Unsupported role category for {task.id}: {task.role_category}"
            )
        if task.story_function not in _ALLOWED_STORY_FUNCTIONS:
            raise ValueError(
                f"Unsupported story function for {task.id}: {task.story_function}"
            )
        if task.verification_class not in _ALLOWED_VERIFICATION_CLASSES:
            raise ValueError(
                "Unsupported verification class for "
                f"{task.id}: {task.verification_class}"
            )
        if not task.name.strip():
            raise ValueError(f"Task {task.id} must have a non-empty name.")
        if not task.operator_description.strip():
            raise ValueError(
                f"Task {task.id} must have a non-empty operator description."
            )
        if not task.substitution_group.strip():
            raise ValueError(
                f"Task {task.id} must have a non-empty substitution group."
            )


_validate_task_library()

__all__ = [
    "TASK_LIBRARY",
    "TaskDefinition",
    "TaskId",
    "TaskRoleCategory",
    "TaskStoryFunction",
    "TaskTier",
    "TaskVerificationClass",
]
