from vi_api.domain.training.policies import evaluate_parts, resolve_label_conflicts


def detection(label, bounds):
    return dict(zip(("x1", "y1", "x2", "y2"), bounds), label=label, confidence=0.9)


def reference(label, bounds):
    x1, y1, x2, y2 = bounds
    return {"label": label, "start": {"x": x1, "y": y1}, "end": {"x": x2, "y": y2}}


def test_competing_labels_do_not_count_one_part_twice():
    left = (0.1, 0.1, 0.3, 0.3)
    right = (0.6, 0.6, 0.8, 0.8)
    snapshot = {
        "part_name": "Assembly",
        "photos": [{"boxes": [reference("Bracket", left), reference("Clip", right)]}],
    }
    expected = {"Bracket": 1, "Clip": 1}
    left_predictions = [detection("Bracket", left), detection("Clip", left)]
    complete = left_predictions + [
        detection("Bracket", right),
        detection("Clip", right),
        detection("Clip", (0.52, 0.52, 0.90, 0.90)),
    ]
    assert evaluate_parts(expected, resolve_label_conflicts(snapshot, expected, complete))["decision"] == "PASS"
    assert evaluate_parts(
        expected, resolve_label_conflicts(snapshot, expected, left_predictions)
    )["decision"] == "FAIL"


def test_nested_parts_and_spatially_distinct_extras_are_retained():
    outer = (0.1, 0.1, 0.4, 0.4)
    inner = (0.13, 0.13, 0.38, 0.38)
    expected = {"Housing": 1, "Plate": 1}
    snapshot = {
        "part_name": "Assembly",
        "photos": [{"boxes": [reference("Housing", outer), reference("Plate", inner)]}],
    }
    correct = [detection("Housing", outer), detection("Plate", inner)]
    assert resolve_label_conflicts(snapshot, expected, correct) == correct
    extra = correct + [detection("Plate", (0.7, 0.7, 0.9, 0.9))]
    assert resolve_label_conflicts(snapshot, expected, extra) == extra


def test_training_options_accept_presets_and_model_sizes():
    import pytest
    from pydantic import ValidationError
    from vi_api.interfaces.http.schemas.training import TrainingOptions

    options = TrainingOptions(preset="accurate", model_size="s", copy_paste=0.2, iou=0.6, max_det=100)
    assert options.preset == "accurate" and options.model_size == "s"
    assert TrainingOptions().model_size == "n" and TrainingOptions().erasing == 0.4
    for invalid in ({"model_size": "xl"}, {"preset": "turbo"}, {"iou": 1.5}, {"max_det": 0}):
        with pytest.raises(ValidationError):
            TrainingOptions(**invalid)
    with pytest.raises(ValidationError):
        TrainingOptions(validation_percent=30, test_percent=30)
