from aquacare import engine
from aquacare.engine import Profile, assess, fish_loss_share

ALL_YES = {k: True for k in engine.CHECK_KEYS}
ALL_NO = {k: False for k in engine.CHECK_KEYS}


def profile(**kw):
    base = dict(farm_type="land", fish=10000, stock=100000, survival_hours=2,
                sales=365000, monthly_payments=20000, insured=True, needs_globalgap=True)
    base.update(kw)
    return Profile(**base)


def test_all_pass_has_nine_passes_and_no_top_fixes():
    r = assess(profile(), ALL_YES)
    assert r.passed_count == 9
    assert r.top_fixes == []
    assert r.fraud_exposure == 0 and r.outage_loss == 0


def test_all_fail_loses_everything_with_short_survival():
    r = assess(profile(survival_hours=2), ALL_NO)
    assert r.current_share == 1.0
    assert r.dollars_at_risk == 100000


def test_fixes_reduce_fish_loss():
    r = assess(profile(survival_hours=10), ALL_NO)
    assert r.fixed_share < r.current_share


def test_share_is_capped_at_one():
    assert fish_loss_share({}, 0.25) == 1.0


def test_alarm_fix_saving_is_positive():
    r = assess(profile(survival_hours=10), ALL_NO)
    alarm = next(c for c in r.results if c.key == "alarm")
    assert alarm.saving > 0


def test_fraud_exposure_equals_monthly_payments():
    r = assess(profile(), {**ALL_YES, "callback": False})
    assert r.fraud_exposure == 20000


def test_outage_loss_uses_daily_sales():
    r = assess(profile(sales=365000), {**ALL_YES, "records": False})
    assert round(r.outage_loss) == 4000  # (5 - 1) days x $1,000/day


def test_netpen_has_no_backup_oxygen_clause():
    checks = engine.build_checks(profile(farm_type="netpen"))
    backup = next(c for c in checks if c["key"] == "backup")
    assert "GLOBALG.A.P. AQ 5.9.5" not in backup["required_by"]


def test_tamper_checks_add_no_double_counted_saving():
    r = assess(profile(), ALL_NO)
    for c in r.results:
        if c.group == "tamper":
            assert c.saving == 0


def test_demos_run():
    for p, a in engine.DEMOS.values():
        assert assess(p, a).passed_count <= 9
