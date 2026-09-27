"""Risk engine for AquaCare.

All model constants below are OUR ASSUMPTIONS, not cited statistics.
They are listed in SOURCES so the report shows them openly.
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------- assumptions
NOTICE_HOURS = {  # hours before anyone notices a failure
    "tested_alarm": 0.25,
    "untested_alarm": 1.0,
    "manual_only": 4.0,
    "nothing": 8.0,
}
RESTORE_HOURS = {"backup": 0.5, "no_backup": 4.0}  # hours to restore life support
OUTAGE_DAYS = {"with_backup": 1, "without_backup": 5}  # ransomware disruption

FARM_TYPES = {
    "netpen": {
        "name": "ocean net-pen",
        "survival_label": "Hours before a net, mooring or water-flow problem starts killing fish",
        "backup": "backup power for your monitoring, alarm and feed systems",
        "manual": "physically check nets, moorings and fish every day",
        "gg_backup_oxygen": False,
    },
    "land": {
        "name": "land-based tank",
        "survival_label": "Hours your fish last if oxygen or water flow stops",
        "backup": "backup oxygen or aeration that starts if power fails",
        "manual": "hand-check oxygen and temperature every shift",
        "gg_backup_oxygen": True,
    },
    "pond": {
        "name": "pond / flow-through",
        "survival_label": "Hours your fish last if aeration stops (think warm summer nights)",
        "backup": "backup aeration or power ready for low-oxygen nights",
        "manual": "check oxygen at night during warm weather",
        "gg_backup_oxygen": True,
    },
    "shell": {
        "name": "shellfish",
        "survival_label": "Hours before an unnoticed line or water problem causes losses",
        "backup": "backup power for your monitoring and alarms",
        "manual": "physically check lines, cages and water every day",
        "gg_backup_oxygen": False,
    },
}

SURVIVAL_HINTS = {
    "pond": "Not sure? Extension guides say to add aeration when oxygen falls below 4 mg/L; "
            "big pond farms check every 2 hours at night (UF/IFAS).",
    "default": "Not sure? It can be minutes in busy tanks: one tank-farm manager raced in after a "
               "5 a.m. power alarm, unsure if fish survived 20 minutes (Global Seafood Alliance).",
}

CHECK_KEYS = ["alarm", "tested", "backup", "manual", "records", "mfa", "callback", "passwords", "network"]


@dataclass
class Profile:
    farm_type: str
    fish: float
    stock: float
    survival_hours: float
    sales: float
    monthly_payments: float
    insured: bool
    needs_globalgap: bool

    @property
    def wording(self):
        return FARM_TYPES.get(self.farm_type, FARM_TYPES["land"])


def build_checks(profile: Profile):
    w = profile.wording
    return [
        dict(key="alarm", group="fish", cost="~US$100-500",
             question="Does an alarm call or text you when power, oxygen or sensors fail, even if the office internet is down?",
             required_by=["Insurer", "GLOBALG.A.P. AQ 5.9.4"],
             fix="Add an auto-dialer alarm that phones 2+ people."),
        dict(key="tested", group="fish", cost="Free",
             question="Do you test that alarm and write down each test?",
             required_by=["GLOBALG.A.P. AQ 5.9.4"],
             fix="Test monthly; log date, who and result."),
        dict(key="backup", group="fish", cost="Get a quote",
             question=f"Do you have {w['backup']}?",
             required_by=["Insurer", "GLOBALG.A.P. AQ 5.9.5"] if w["gg_backup_oxygen"] else ["Insurer"],
             fix=f"Install {w['backup']}."),
        dict(key="manual", group="fish", cost="Free",
             question=f"If screens show wrong numbers, do staff still {w['manual']}?",
             required_by=["Insurer"],
             fix=f"Put a manual check on the daily roster: {w['manual']}."),
        dict(key="records", group="outage", cost="Low cost",
             question="Are stock, feeding and supplier records backed up somewhere offline?",
             required_by=["GLOBALG.A.P. AF 2.1"],
             fix="Weekly copy to an unplugged drive or a separate account."),
        dict(key="mfa", group="fraud", cost="Free",
             question="Does logging into email, banking and the farm dashboard need a code from your phone?",
             required_by=["Insurer (cyber cover)", "Cyber Centre"],
             fix="Turn on 2-step login for email, bank and dashboard."),
        dict(key="callback", group="fraud", cost="Free",
             question="Before changing a supplier's bank details, do you phone them on a number you already had?",
             required_by=["Anti-Fraud Centre advice"],
             fix="Rule: no bank change without a call to a known number."),
        dict(key="passwords", group="tamper", cost="Free",
             question="Have factory passwords been changed on sensors, feeders, pumps and routers?",
             required_by=["Cyber Centre"],
             fix="Change every factory password; keep the list offline."),
        dict(key="network", group="tamper", cost="Low cost",
             question="Is farm equipment on its own network, separate from office and guest Wi-Fi?",
             required_by=["Cyber Centre"],
             fix="Put equipment on a separate network; remove always-on vendor access."),
    ]


def fish_loss_share(answers: dict, survival_hours: float) -> float:
    """Share of stock lost in one unnoticed failure (0-1)."""
    if answers.get("alarm"):
        notice = NOTICE_HOURS["tested_alarm"] if answers.get("tested") else NOTICE_HOURS["untested_alarm"]
    else:
        notice = NOTICE_HOURS["manual_only"] if answers.get("manual") else NOTICE_HOURS["nothing"]
    restore = RESTORE_HOURS["backup"] if answers.get("backup") else RESTORE_HOURS["no_backup"]
    survival = max(survival_hours or 2, 0.25)
    return min(1.0, (notice + restore) / survival)


def outage_cost(profile: Profile) -> float:
    return (OUTAGE_DAYS["without_backup"] - OUTAGE_DAYS["with_backup"]) * profile.sales / 365


def money(n: float) -> str:
    return f"${round(n):,}"


def count(n: float) -> str:
    return f"{round(n):,}"


@dataclass
class CheckResult:
    key: str
    question: str
    required_by: list
    fix: str
    cost: str
    group: str
    passed: bool
    loss_text: str = ""
    saving: float = 0.0


@dataclass
class Report:
    profile: Profile
    current_share: float
    fixed_share: float
    results: list = field(default_factory=list)

    @property
    def fish_at_risk(self):
        return self.current_share * self.profile.fish

    @property
    def dollars_at_risk(self):
        return self.current_share * self.profile.stock

    @property
    def fish_after_fixes(self):
        return self.fixed_share * self.profile.fish

    @property
    def dollars_after_fixes(self):
        return self.fixed_share * self.profile.stock

    @property
    def passed_count(self):
        return sum(r.passed for r in self.results)

    @property
    def fraud_exposure(self):
        is_open = any(not r.passed and r.group == "fraud" for r in self.results)
        return self.profile.monthly_payments if is_open else 0.0

    @property
    def outage_loss(self):
        rec = next(r for r in self.results if r.key == "records")
        return 0.0 if rec.passed else outage_cost(self.profile)

    @property
    def insurer_gaps(self):
        return [r for r in self.results if not r.passed and any(x.startswith("Insurer") for x in r.required_by)]

    @property
    def globalgap_gaps(self):
        return [r for r in self.results if not r.passed and any(x.startswith("GLOBALG") for x in r.required_by)]

    @property
    def top_fixes(self):
        return sorted([r for r in self.results if not r.passed], key=lambda r: r.saving, reverse=True)[:3]


def assess(profile: Profile, answers: dict) -> Report:
    """answers: {check_key: True/False}"""
    cur = fish_loss_share(answers, profile.survival_hours)
    fixed = fish_loss_share({"alarm": True, "tested": True, "backup": True, "manual": True}, profile.survival_hours)
    report = Report(profile=profile, current_share=cur, fixed_share=fixed)

    for c in build_checks(profile):
        passed = bool(answers.get(c["key"]))
        loss, saving = "", 0.0
        if not passed:
            if c["group"] == "fish":
                after = fish_loss_share({**answers, c["key"]: True}, profile.survival_hours)
                saving = (cur - after) * profile.stock
                loss = (f"One unnoticed failure: {count(cur * profile.fish)} fish ({money(cur * profile.stock)}) lost. "
                        f"Fixing this alone saves about {money(saving)}.")
            elif c["group"] == "outage":
                saving = outage_cost(profile)
                loss = (f"Ransomware could stop records and sales for ~{OUTAGE_DAYS['without_backup']} days "
                        f"instead of ~{OUTAGE_DAYS['with_backup']}: {money(saving)} in lost sales.")
            elif c["group"] == "fraud":
                saving = profile.monthly_payments
                if c["key"] == "mfa":
                    loss = (f"A stolen email login is how fake invoices start: up to {money(saving)} "
                            f"(one month of supplier payments). 2-step login blocks 99.2% of account takeovers.")
                else:
                    loss = (f"One fake 'new bank details' email could divert {money(saving)} "
                            f"(one month of supplier payments).")
            else:  # tamper: shows exposure only, no separate saving (avoids double counting)
                loss = (f"Leaves equipment open to tampering, putting {count(cur * profile.fish)} fish "
                        f"({money(cur * profile.stock)}) in play.")
        report.results.append(CheckResult(passed=passed, loss_text=loss, saving=saving, **c))
    return report


SOURCES = [
    "Fish loss = stock x (time to notice + time to restore) / your survival hours, capped at 100%. "
    "Our assumptions: notice in 15 min with a tested alarm, 1 h untested, 4 h with manual checks only, 8 h with neither; "
    "restore in 30 min with backup, 4 h without. Survival hours come from you: no reliable table exists by farm type.",
    "Ransomware outage: ~5 days without offline backups vs ~1 with (our assumption), valued at your daily sales.",
    "Fraud exposure = one month of supplier payments (our assumption). Spear-phishing cost Canadian businesses "
    "$67.5M reported in 2024, and only 5-10% of victims report (Canadian Anti-Fraud Centre).",
    "Insurers survey alarms, backups and staff response and can make them policy conditions; non-disclosure can "
    "void a policy (FAO Fisheries Technical Paper on aquaculture insurance).",
    "GLOBALG.A.P. Aquaculture v5.4: AF 2.1 backed-up electronic records; AQ 5.9.4 alarms on automatic systems plus "
    "test records; AQ 5.9.5 backup oxygen. Annual audits plus unannounced visits (GLOBALG.A.P. General Regulations).",
    "Auto-dialer alarms cost about US$100-500; power loss wipes out whole tank facilities several times a year "
    "(Global Seafood Alliance, 'Backup oxygen, power systems essential insurance').",
    "2-step login blocked 99.22% of account compromises (Microsoft Research). Insurers increasingly require it "
    "for cyber cover (McCarthy Tetrault).",
    "Password and network checks follow the Canadian Centre for Cyber Security baseline controls for small organizations.",
]

DEMOS = {
    "netpen": (
        Profile("netpen", 180000, 850000, 10, 2400000, 60000, True, True),
        dict(alarm=True, tested=False, backup=True, manual=True, records=False,
             mfa=False, callback=False, passwords=False, network=False),
    ),
    "ras": (
        Profile("land", 45000, 220000, 2, 650000, 18000, True, False),
        dict(alarm=False, tested=False, backup=False, manual=False, records=False,
             mfa=False, callback=True, passwords=False, network=False),
    ),
}
