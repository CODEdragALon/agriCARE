from app import app

PROFILE = dict(farm_type="land", fish="1000", stock="50000", survival_hours="2", sales="100000",
               monthly_payments="5000", insured="yes", needs_globalgap="yes")


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_home():
    assert client().get("/").status_code == 200


def test_checks_requires_profile():
    assert client().post("/checks", data={}).status_code == 400


def test_full_flow():
    c = client()
    assert c.post("/checks", data=PROFILE).status_code == 200
    answers = {k: "no" for k in ["alarm", "tested", "backup", "manual", "records", "mfa", "callback", "passwords", "network"]}
    r = c.post("/report", data={**PROFILE, **answers})
    assert r.status_code == 200 and b"FIX" in r.data


def test_report_rejects_missing_answers():
    assert client().post("/report", data=PROFILE).status_code == 400


def test_demos():
    c = client()
    for k in ("netpen", "ras"):
        assert c.get(f"/demo/{k}").status_code == 200
    assert c.get("/demo/nope").status_code == 404
