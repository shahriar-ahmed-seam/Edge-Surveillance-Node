from src.mqtt_client import MqttPublisher


class FakeClient:
    def __init__(self):
        self.published = []
        self.fail_publish = False
        self.on_connect = None
        self.on_disconnect = None

    def publish(self, topic, payload, qos=1):
        if self.fail_publish:
            class Info:
                rc = 1

            return Info()
        self.published.append((topic, payload))

        class Info:
            rc = 0

        return Info()


def _make(**kw):
    client = FakeClient()
    pub = MqttPublisher(
        host="h", port=8883, username="u", password="p", node_id="n1",
        use_tls=False, client_factory=lambda: client, **kw
    )
    pub._client = client
    return pub, client


def test_publish_when_connected_sends_immediately():
    pub, client = _make()
    pub._connected = True
    assert pub.publish("t", {"a": 1}) is True
    assert len(client.published) == 1


def test_publish_when_disconnected_buffers():
    pub, client = _make()
    pub._connected = False
    assert pub.publish("t", {"a": 1}) is False
    assert pub.queue_depth == 1


def test_outbox_drops_oldest_when_full():
    pub, client = _make(outbox_max_size=2)
    pub._connected = False
    for i in range(4):
        pub.publish("t", {"i": i})
    assert pub.queue_depth == 2  # bounded
    assert pub.dropped_count == 2


def test_no_republish_without_disconnect():
    pub, client = _make()
    # connect with no prior disconnect and empty queue -> no flush activity
    pub._on_connect(client, None, None, 0)
    assert client.published == []


def test_republish_only_after_real_disconnect():
    pub, client = _make()
    pub._connected = False
    pub.publish("t", {"a": 1})  # buffered
    pub._had_disconnect = True   # simulate prior disconnect
    pub._on_connect(client, None, None, 0)
    assert len(client.published) == 1  # flushed in order
    assert pub.queue_depth == 0


def test_empty_queue_after_disconnect_does_not_republish():
    pub, client = _make()
    pub._had_disconnect = True
    pub._on_connect(client, None, None, 0)  # queue empty
    assert client.published == []
