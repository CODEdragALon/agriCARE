"""AquaCyber Flask app. Run: flask --app app run"""
from flask import Flask, render_template, request, abort
from aquacyber import engine

app = Flask(__name__)
app.jinja_env.globals.update(money=engine.money, count=engine.count)

PROFILE_FIELDS = ["farm_type", "fish", "stock", "survival_hours", "sales", "monthly_payments", "insured", "needs_globalgap"]


def _num(v, default=0.0):
    try:
        return max(float(v), 0.0)
    except (TypeError, ValueError):
        return default


def profile_from(form):
    return engine.Profile(
        farm_type=form.get("farm_type", "land"),
        fish=_num(form.get("fish")),
        stock=_num(form.get("stock")),
        survival_hours=_num(form.get("survival_hours"), 2),
        sales=_num(form.get("sales")),
        monthly_payments=_num(form.get("monthly_payments")),
        insured=form.get("insured") == "yes",
        needs_globalgap=form.get("needs_globalgap") == "yes",
    )


@app.get("/")
def profile_page():
    return render_template("profile.html", farm_types=engine.FARM_TYPES, hints=engine.SURVIVAL_HINTS, error=None)


@app.post("/checks")
def checks_page():
    f = request.form
    if not f.get("farm_type") or _num(f.get("stock")) <= 0 or _num(f.get("survival_hours")) <= 0 \
            or f.get("insured") not in ("yes", "no") or f.get("needs_globalgap") not in ("yes", "no"):
        return render_template("profile.html", farm_types=engine.FARM_TYPES, hints=engine.SURVIVAL_HINTS,
                               error="Please fill in farm type, stock value, survival hours and both yes/no questions."), 400
    profile = profile_from(f)
    hidden = {k: f.get(k, "") for k in PROFILE_FIELDS}
    return render_template("checks.html", checks=engine.build_checks(profile), hidden=hidden, error=None)


@app.post("/report")
def report_page():
    f = request.form
    profile = profile_from(f)
    missing = [k for k in engine.CHECK_KEYS if f.get(k) not in ("yes", "no")]
    if missing:
        hidden = {k: f.get(k, "") for k in PROFILE_FIELDS}
        return render_template("checks.html", checks=engine.build_checks(profile), hidden=hidden,
                               error=f"Answer all 9 checks ({len(missing)} left)."), 400
    answers = {k: f.get(k) == "yes" for k in engine.CHECK_KEYS}
    return render_template("report.html", r=engine.assess(profile, answers), sources=engine.SOURCES)


@app.get("/demo/<kind>")
def demo(kind):
    if kind not in engine.DEMOS:
        abort(404)
    profile, answers = engine.DEMOS[kind]
    return render_template("report.html", r=engine.assess(profile, answers), sources=engine.SOURCES)


if __name__ == "__main__":
    app.run(debug=True)
