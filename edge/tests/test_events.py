from src.events import Detection, EventFactory


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_below_threshold_produces_no_event():
    f = EventFactory("n1", confidence_threshold=0.5)
    event = f.build([Detection("person", 0.3, [0, 0, 1, 1])])
    assert event is None


def test_above_threshold_produces_event():
    f = EventFactory("n1", confidence_threshold=0.5)
    event = f.build([Detection("person", 0.8, [0, 0, 1, 1])])
    assert event is not None
    assert event["node_id"] == "n1"
    assert event["detections"][0]["label"] == "person"
    assert "event_id" in event and "timestamp" in event


def test_debounce_suppresses_repeated_class():
    clock = FakeClock()
    f = EventFactory("n1", confidence_threshold=0.5, debounce_seconds=5.0, clock=clock)
    assert f.build([Detection("person", 0.9, [0, 0, 1, 1])]) is not None
    clock.t = 2.0
    assert f.build([Detection("person", 0.9, [0, 0, 1, 1])]) is None  # within debounce
    clock.t = 6.0
    assert f.build([Detection("person", 0.9, [0, 0, 1, 1])]) is not None  # after cooldown


def test_debounce_is_per_class():
    clock = FakeClock()
    f = EventFactory("n1", confidence_threshold=0.5, debounce_seconds=5.0, clock=clock)
    f.build([Detection("person", 0.9, [0, 0, 1, 1])])
    clock.t = 1.0
    # different class is not debounced
    event = f.build([Detection("car", 0.9, [0, 0, 1, 1])])
    assert event is not None


def test_snapshot_meta_attached():
    f = EventFactory("n1", confidence_threshold=0.5)
    meta = {"present": True, "bytes": 100}
    event = f.build([Detection("person", 0.9, [0, 0, 1, 1])], snapshot_meta=meta)
    assert event["snapshot"] == meta
