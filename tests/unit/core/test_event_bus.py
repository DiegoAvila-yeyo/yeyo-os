"""Tests para Event Bus — Micro-fase 1.9"""

import pytest
from src.core.event_bus import EventBus, SYSTEM_EVENTS


@pytest.fixture
def bus():
    EventBus.reset_instance()
    b = EventBus()
    yield b
    b.clear()


class TestEventBusSingleton:
    def test_singleton_returns_same_instance(self):
        EventBus.reset_instance()
        b1 = EventBus.instance()
        b2 = EventBus.instance()
        assert b1 is b2

    def test_reset_creates_new_instance(self):
        EventBus.reset_instance()
        b1 = EventBus.instance()
        EventBus.reset_instance()
        b2 = EventBus.instance()
        assert b1 is not b2


class TestEventBusSubscribe:
    def test_subscribe_adds_callback(self, bus):
        async def handler(data): pass
        bus.subscribe("test.event", handler)
        assert bus.get_subscriber_count("test.event") == 1

    def test_subscribe_multiple_callbacks(self, bus):
        async def handler1(data): pass
        async def handler2(data): pass
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        assert bus.get_subscriber_count("test.event") == 2

    def test_subscribe_same_callback_once(self, bus):
        async def handler(data): pass
        bus.subscribe("test.event", handler)
        bus.subscribe("test.event", handler)
        assert bus.get_subscriber_count("test.event") == 1

    def test_unsubscribe_removes_callback(self, bus):
        async def handler(data): pass
        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)
        assert bus.get_subscriber_count("test.event") == 0

    def test_unsubscribe_nonexistent_is_safe(self, bus):
        async def handler(data): pass
        bus.unsubscribe("nonexistent.event", handler)

    def test_get_subscriber_count_no_event(self, bus):
        assert bus.get_subscriber_count("nonexistent") == 0


class TestEventBusPublish:
    @pytest.mark.asyncio
    async def test_publish_calls_subscriber(self, bus):
        received = []
        async def handler(data): received.append(data)
        bus.subscribe("test.event", handler)
        await bus.publish("test.event", {"key": "value"})
        assert received[0] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_publish_calls_all_subscribers(self, bus):
        results = []
        async def handler1(data): results.append("h1")
        async def handler2(data): results.append("h2")
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        await bus.publish("test.event", None)
        assert "h1" in results and "h2" in results

    @pytest.mark.asyncio
    async def test_publish_no_subscribers_is_safe(self, bus):
        await bus.publish("nonexistent.event", {"data": 1})

    @pytest.mark.asyncio
    async def test_publish_with_none_data(self, bus):
        received = []
        async def handler(data): received.append(data)
        bus.subscribe("test.event", handler)
        await bus.publish("test.event")
        assert received[0] is None

    @pytest.mark.asyncio
    async def test_subscriber_error_doesnt_affect_others(self, bus):
        results = []
        async def bad_handler(data): raise RuntimeError("Error intencional")
        async def good_handler(data): results.append("ok")
        bus.subscribe("test.event", bad_handler)
        bus.subscribe("test.event", good_handler)
        await bus.publish("test.event", None)
        assert "ok" in results

    @pytest.mark.asyncio
    async def test_publish_only_to_matching_event(self, bus):
        results = []
        async def handler_a(data): results.append("a")
        async def handler_b(data): results.append("b")
        bus.subscribe("event.a", handler_a)
        bus.subscribe("event.b", handler_b)
        await bus.publish("event.a", None)
        assert results == ["a"]


class TestEventBusUtility:
    def test_clear_removes_all(self, bus):
        async def handler(data): pass
        bus.subscribe("event.a", handler)
        bus.subscribe("event.b", handler)
        bus.clear()
        assert bus.get_subscriber_count("event.a") == 0

    def test_get_all_event_types(self, bus):
        async def handler(data): pass
        bus.subscribe("event.a", handler)
        bus.subscribe("event.b", handler)
        types = bus.get_all_event_types()
        assert "event.a" in types and "event.b" in types


class TestSystemEvents:
    def test_system_events_are_strings(self):
        for event in SYSTEM_EVENTS:
            assert isinstance(event, str)

    def test_gpu_events_exist(self):
        assert "gpu.task.started" in SYSTEM_EVENTS
        assert "gpu.task.completed" in SYSTEM_EVENTS

    def test_memory_events_exist(self):
        assert "memory.stored" in SYSTEM_EVENTS
        assert "memory.recalled" in SYSTEM_EVENTS

    def test_chat_events_exist(self):
        assert "chat.message" in SYSTEM_EVENTS

    def test_system_events_exist(self):
        assert "system.error" in SYSTEM_EVENTS

    def test_node_events_exist(self):
        assert "node.opened" in SYSTEM_EVENTS
        assert "node.closed" in SYSTEM_EVENTS
