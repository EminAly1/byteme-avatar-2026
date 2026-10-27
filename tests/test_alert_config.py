"""Explicit review thresholds, no inferred business standard or float quantity."""
import os
from decimal import Decimal
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.config import Settings


@pytest.fixture(autouse=True)
def isolated_policy_environment(monkeypatch):
    for key in list(os.environ):
        if key.startswith('AVATAR_ALERT_'):
            monkeypatch.delenv(key)


def test_default_policy_has_no_invented_low_stock_threshold():
    settings = Settings()
    assert settings.avatar_alert_stock_thresholds == {}
    assert settings.avatar_alert_cost_percent == settings.avatar_alert_yield_percent == Decimal('15')
    assert settings.avatar_alert_deviation_origin == 'demo'


def test_json_environment_threshold_uses_uuid_unit_decimal_and_origin(monkeypatch):
    identifier = str(uuid4())
    monkeypatch.setenv('AVATAR_ALERT_STOCK_THRESHOLDS', json.dumps({identifier: {'quantity': '2.000001', 'unit': 'kg', 'origin': 'demo'}}))
    settings = Settings()
    threshold = settings.avatar_alert_stock_thresholds[next(iter(settings.avatar_alert_stock_thresholds))]
    assert str(next(iter(settings.avatar_alert_stock_thresholds))) == identifier
    assert threshold.quantity == Decimal('2.000001') and threshold.origin == 'demo'


@pytest.mark.parametrize('value', [
    {'quantity': 3.5, 'unit': 'kg'}, {'quantity': '0', 'unit': 'kg'},
    {'quantity': '-1', 'unit': 'kg'}, {'quantity': 'NaN', 'unit': 'kg'},
    {'quantity': '3.0000001', 'unit': 'kg'}, {'quantity': '1.5', 'unit': 'package'},
    {'quantity': '1.5', 'unit': 'unit'}, {'quantity': '1', 'unit': 'lb'},
])
def test_invalid_explicit_threshold_rejected(value):
    with pytest.raises(ValidationError):
        Settings(avatar_alert_stock_thresholds={str(uuid4()): value})


@pytest.mark.parametrize('values', [
    {'avatar_alert_expiry_days': -1}, {'avatar_alert_expiry_days': 31},
    {'avatar_alert_cost_percent': '0'}, {'avatar_alert_yield_percent': 'NaN'},
    {'avatar_alert_policy_version': '../private'},
    {'avatar_alert_stock_thresholds': {str(uuid4()): {'quantity': '1', 'unit': 'kg'} for _ in range(201)}},
])
def test_invalid_policy_settings_fail_validation(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_policy_identity_normalizes_equivalent_decimal_spelling():
    from app.alerts import policy
    identifier = str(uuid4())
    first = Settings(avatar_alert_stock_thresholds={identifier: {'quantity': '2', 'unit': 'kg'}}, avatar_alert_cost_percent='15')
    second = Settings(avatar_alert_stock_thresholds={identifier: {'quantity': '2.000000', 'unit': 'kg'}}, avatar_alert_cost_percent='15.0000')
    assert policy(first)['fingerprint'] == policy(second)['fingerprint']
