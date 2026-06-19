import pytest

from app.utils.status_flow_buckets import (
    FLOW_BUCKET_DEV,
    FLOW_BUCKET_DONE,
    FLOW_BUCKET_OTHER,
    FLOW_BUCKET_PAUSE,
    FLOW_BUCKET_TEST,
    FLOW_BUCKET_TODO,
    classify_status_flow_bucket,
)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Готово", FLOW_BUCKET_DONE),
        ("Done", FLOW_BUCKET_DONE),
        ("Backlog", FLOW_BUCKET_TODO),
        ("К выполнению", FLOW_BUCKET_TODO),
        ("To Do", FLOW_BUCKET_TODO),
        ("Пауза", FLOW_BUCKET_PAUSE),
        ("On Hold", FLOW_BUCKET_PAUSE),
        ("Blocked", FLOW_BUCKET_PAUSE),
        ("В работе", FLOW_BUCKET_DEV),
        ("In Progress", FLOW_BUCKET_DEV),
        ("Code Review", FLOW_BUCKET_DEV),
        ("Ревью", FLOW_BUCKET_DEV),
        ("Тестирование", FLOW_BUCKET_TEST),
        ("К тестированию", FLOW_BUCKET_TEST),
        ("К релизу", FLOW_BUCKET_TEST),
        ("Ready for Release", FLOW_BUCKET_TEST),
        ("Custom Active Step", FLOW_BUCKET_DEV),
        ("", FLOW_BUCKET_OTHER),
    ],
)
def test_classify_status_flow_bucket(status: str, expected: str) -> None:
    assert classify_status_flow_bucket(status) == expected
