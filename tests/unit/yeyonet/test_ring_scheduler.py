import pytest

from src.yeyonet.ring_scheduler import NoEligibleRingNodeError, RingScheduler


def test_assign_steps_alternates_between_two_nodes():
    scheduler = RingScheduler()
    ring = ["pc1", "pc2"]
    steps = [
        {"step_type": "prepare_prompt", "requirements": {}},
        {"step_type": "generate_image", "requirements": {"needs_gpu": True}},
        {"step_type": "store_result", "requirements": {}},
        {"step_type": "publish_result", "requirements": {}},
    ]
    capabilities = {
        "pc1": {},
        "pc2": {"gpu_name": "RTX 4090", "ram_free_gb": 8.0},
    }

    assignments = scheduler.assign_steps(ring, steps, capabilities)

    assert [(assignment.node_id, assignment.ring_index) for assignment in assignments] == [
        ("pc1", 0),
        ("pc2", 1),
        ("pc1", 0),
        ("pc2", 1),
    ]


def test_assign_steps_skips_ineligible_node_but_preserves_ring():
    scheduler = RingScheduler()
    ring = ["pc1", "pc2"]
    steps = [
        {"step_type": "prepare_prompt", "requirements": {}},
        {"step_type": "generate_image", "requirements": {"needs_gpu": True}},
    ]
    capabilities = {
        "pc1": {"gpu_name": "Apple M1", "ram_free_gb": 8.0},
        "pc2": {"ram_free_gb": 8.0},
    }

    assignments = scheduler.assign_steps(ring, steps, capabilities)

    assert [(assignment.node_id, assignment.ring_index) for assignment in assignments] == [
        ("pc1", 0),
        ("pc1", 0),
    ]


def test_assign_steps_raises_when_no_node_can_run_step():
    scheduler = RingScheduler()

    with pytest.raises(NoEligibleRingNodeError):
        scheduler.assign_steps(
            ["pc1", "pc2"],
            [{"step_type": "generate_image", "requirements": {"needs_gpu": True}}],
            {"pc1": {}, "pc2": {}},
        )
