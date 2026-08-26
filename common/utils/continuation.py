"""Fail-closed checks for matched-continuation runs.

A matched continuation is a run whose scientific meaning depends on starting
from an exact, fully specified state: the same weights, the same optimizer
moments, the same LR-schedule position and the same step counter as every
sibling arm.  The ordinary training path is tolerant -- a missing or
unreadable field prints a warning and training proceeds from scratch or from a
reset optimizer.  That tolerance turns a typo into a silently different
experiment, so a run that declares a continuation budget opts into these
checks instead.

Kept out of the trainer so it can be tested without a GPU, a dataset or a
distributed process group.
"""

# Fields a resumable parent must carry.  `global_step` is on the list for a
# specific reason: it anchors the RMLF rollout warmup ramp, and reading it with
# a default of 0 makes "absent" indistinguishable from "genuinely zero".
REQUIRED_CONTINUATION_FIELDS = (
    "preload_model path",
    "model_state_dict",
    "optimizer_state_dict",
    "scheduler_state_dict",
    "epoch",
    "global_step",
    "mean",
    "std",
)


def missing_continuation_fields(fields):
    """Return the names in ``fields`` whose value is ``None``.

    ``fields`` is an ordered mapping of ``name -> value``.  Only ``None``
    counts as missing: ``0``, ``0.0`` and empty tensors are legitimate values,
    which is exactly why callers must not substitute defaults before checking.
    """
    unknown = set(fields).difference(REQUIRED_CONTINUATION_FIELDS)
    if unknown:
        raise ValueError(
            f"unexpected continuation fields: {sorted(unknown)}; expected a "
            f"subset of {list(REQUIRED_CONTINUATION_FIELDS)}"
        )
    return [name for name, value in fields.items() if value is None]


def assert_strict_continuation(fields, parent_path):
    """Raise unless every required continuation field is present."""
    missing = missing_continuation_fields(fields)
    if not missing:
        return
    raise RuntimeError(
        "Strict continuation requires a full resumable parent checkpoint, but "
        f"these fields are missing: {missing}.\n"
        f"  parent: {parent_path}\n"
        "A matched continuation cannot start from a weights-only snapshot: the "
        "optimizer moments, the LR-schedule position and the step counter are "
        "part of what is being matched across arms."
    )
