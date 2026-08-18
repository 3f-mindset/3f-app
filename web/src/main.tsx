import { CSSProperties, ReactNode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DEVELOPMENT_MODE = import.meta.env.DEV;

type Strike = { action: string; measure: string };
type Dashboard = {
  name: string; role: "participant" | "coach" | "captain" | "administrator" | null; coach_name: string; current_week: number; calibration_count: number;
  season_plan: { season_name: string } | null;
  latest_calibration: { aim: string; momentum_level: string; role_to_forge: string; strikes: Strike[] } | null;
  latest_review: { feedback: string } | null;
  direct_reports: DevelopmentAccount[];
};
type DevelopmentAccount = { member_id: string; name: string; role: "participant" | "coach" | "captain" | "administrator" };
type ScaleItem = { value: string; level: number; label: string; definition: string };
type OutboxItem = { id: string; endpoint: string; body: unknown };
type DeckStep = { section: string; prompt: string; hint?: string; content: ReactNode };

const defaultPlan = {
  season_name: "The Stewardship Season", review_day: "Sunday", review_time: "18:00",
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
  roles: "Man, Builder", values: "Presence, Courage, Responsibility", domain: "Health",
  current_reality: "Right now, my health lacks a repeatable weekly rhythm.",
  outcome: "By the end of this 12-week season, I will have trained four days per week for 10 of 12 weeks.",
  protected_time: "Monday, Tuesday, Thursday, Friday at 6:30am", action: "Strength training",
  boundary: "No late scrolling before training days.", evidence: "Four completed training sessions.",
  weekly_actions: "Train four times", scoreboard_measure: "4 workouts completed",
  elimination_action: "reduce", elimination: "Late-night scrolling",
};
const defaultRead = {
  aim: "Build a life ordered around faithful stewardship.", momentum_level: "clearing",
  momentum_evidence: "I addressed a conversation I had been avoiding.",
  meaningful_moment: "Dinner with my family without my phone.", why_it_mattered: "I was fully present instead of distracted.",
  value_in_focus: "Presence", value_most_neglected: "Courage", role: "Man", responsibility_level: "grounded",
  responsibility_evidence: "I kept my morning and evening commitments.",
  avoided: "I avoided the difficult budget review.", drain: "Late work messages drained more attention than they should have.",
  unreleased_weight: "I am carrying frustration from an unfinished conversation.", role_to_forge: "Man",
  strike_one: "Complete the budget review", measure_one: "30 focused minutes on Saturday",
  strike_two: "Protect one phone-free family dinner", measure_two: "One dinner without devices",
};

const ROLE_OPTIONS = [
  "Man", "Husband", "Father", "Son", "Brother", "Friend", "Neighbor", "Mentor",
  "Leader", "Builder", "Provider", "Protector", "Employee", "Business Owner", "Teammate", "Partner",
  "Caregiver", "Student", "Creator", "Athlete", "Volunteer", "Church Member", "Citizen", "Steward",
];
const VALUE_OPTIONS = [
  "Courage", "Integrity", "Presence", "Discipline", "Faith", "Responsibility", "Service", "Patience",
  "Honesty", "Humility", "Excellence", "Generosity", "Loyalty", "Wisdom", "Resilience", "Stewardship",
  "Compassion", "Gratitude", "Justice", "Kindness", "Self-Control", "Diligence", "Simplicity", "Truth",
  "Dependability", "Hospitality", "Forgiveness", "Curiosity", "Order", "Craftsmanship", "Commitment", "Peace",
];

const split = (text: string) => text.split(",").map((item) => item.trim()).filter(Boolean);
const commandId = () => crypto.randomUUID();
const loadOutbox = (): OutboxItem[] => JSON.parse(localStorage.getItem("threef-outbox") ?? "[]") as OutboxItem[];
const queue = (item: OutboxItem) => localStorage.setItem("threef-outbox", JSON.stringify([...loadOutbox(), item]));

async function send(item: OutboxItem) {
  const response = await fetch(`${API}${item.endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(item.body) });
  if (!response.ok) throw new Error((await response.json()).detail ?? "Unable to synchronize");
}

function Field({ value, onChange, multiline = false, placeholder }: { value: string; onChange: (value: string) => void; multiline?: boolean; placeholder?: string }) {
  if (multiline) return <textarea autoFocus value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />;
  return <input autoFocus value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />;
}

function Scale({ value, items, onChange }: { value: string; items: ScaleItem[]; onChange: (value: string) => void }) {
  return <div className="scale">{items.map((item) => <button type="button" title={item.definition} className={value === item.value ? "selected" : ""} onClick={() => onChange(item.value)} key={item.value}><b>{item.level}</b><span>{item.label}</span></button>)}</div>;
}

function DiagnosticSlider({ title, lowLabel, highLabel, value, items, onChange }: { title: string; lowLabel: string; highLabel: string; value: string; items: ScaleItem[]; onChange: (value: string) => void }) {
  const currentIndex = Math.max(0, items.findIndex((item) => item.value === value));
  const current = items[currentIndex] ?? items[0];
  const fill = items.length > 1 ? (currentIndex / (items.length - 1)) * 100 : 0;
  return <div className="diagnostic-slider">
    <div className="diagnostic-read" key={current?.value} style={{ "--read-progress": `${fill}%` } as CSSProperties}>
      <span>{title} · {current?.level} of {items.length}</span>
      <strong>{current?.label}</strong>
      <p>{current?.definition}</p>
    </div>
    <input aria-label={title} type="range" min="1" max={items.length} step="1" value={currentIndex + 1} onChange={(event) => onChange(items[Number(event.target.value) - 1].value)} />
    <div className="slider-labels"><span>{lowLabel}</span><span>{highLabel}</span></div>
  </div>;
}

function ChoicePicker({ options, value, onChange }: { options: string[]; value: string; onChange: (value: string) => void }) {
  if (options.length === 0) return <p className="empty-values">Choose values or roles in your Season Plan before this calibration.</p>;
  return <div className="chip-picker" role="radiogroup">{options.map((option) => <button type="button" role="radio" aria-checked={value === option} className={value === option ? "selected" : ""} onClick={() => onChange(option)} key={option}>{option}</button>)}</div>;
}

function ChipPicker({ options, selected, onChange }: { options: string[]; selected: string[]; onChange: (selected: string[]) => void }) {
  return <div className="chip-picker" role="group">{options.map((option) => {
    const active = selected.includes(option);
    return <button type="button" className={active ? "selected" : ""} aria-pressed={active} onClick={() => onChange(active ? selected.filter((item) => item !== option) : [...selected, option])} key={option}>{option}</button>;
  })}</div>;
}

function Deck({ eyebrow, steps, submitLabel, onSubmit }: { eyebrow: string; steps: DeckStep[]; submitLabel: string; onSubmit: () => void }) {
  const [step, setStep] = useState(0);
  const current = steps[step];
  const last = step === steps.length - 1;
  return <section className="deck" aria-label={eyebrow}>
    <div className="deck-topline"><span>{eyebrow}</span><span>{step + 1} / {steps.length}</span></div>
    <div className="progress"><i style={{ width: `${((step + 1) / steps.length) * 100}%` }} /></div>
    <div className="deck-card" key={step}>
      <p className="eyebrow">{current.section}</p>
      <h1>{current.prompt}</h1>
      {current.hint && <p className="lead">{current.hint}</p>}
      <div className="answer">{current.content}</div>
    </div>
    <div className="deck-actions">
      <button type="button" className="back" onClick={() => setStep((value) => value - 1)} disabled={step === 0}>Back</button>
      <button type="button" className="primary" onClick={() => last ? onSubmit() : setStep((value) => value + 1)}>{last ? submitLabel : "Continue"}</button>
    </div>
  </section>;
}

function App() {
  const [screen, setScreen] = useState<"anvil" | "plan" | "calibration">("anvil");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [accounts, setAccounts] = useState<DevelopmentAccount[]>([]);
  const [activeMemberId, setActiveMemberId] = useState(() => localStorage.getItem("threef-development-account") ?? "demo-member");
  const [momentum, setMomentum] = useState<ScaleItem[]>([]);
  const [responsibility, setResponsibility] = useState<ScaleItem[]>([]);
  const [plan, setPlan] = useState(() => ({ ...defaultPlan, ...JSON.parse(localStorage.getItem("threef-plan-draft") ?? "{}") }));
  const [read, setRead] = useState(() => ({ ...defaultRead, ...JSON.parse(localStorage.getItem("threef-read-draft") ?? "{}") }));
  const [notice, setNotice] = useState("");
  const [online, setOnline] = useState(navigator.onLine);

  const refresh = () => fetch(`${API}/api/dashboard/${activeMemberId}`).then((response) => response.json()).then(setDashboard).catch(() => setNotice("Working offline. Your drafts are safe on this device."));
  useEffect(() => {
    refresh();
    if (DEVELOPMENT_MODE) fetch(`${API}/api/development/accounts`).then((response) => response.ok ? response.json() : []).then(setAccounts).catch(() => undefined);
    fetch(`${API}/api/reference/scales`).then((response) => response.json()).then((data) => { setMomentum(data.momentum); setResponsibility(data.responsibility); }).catch(() => undefined);
    const reconnect = () => {
      setOnline(true);
      void (async () => {
        const remaining: OutboxItem[] = [];
        for (const item of loadOutbox()) { try { await send(item); } catch { remaining.push(item); } }
        localStorage.setItem("threef-outbox", JSON.stringify(remaining)); refresh();
      })();
    };
    const disconnect = () => setOnline(false);
    window.addEventListener("online", reconnect); window.addEventListener("offline", disconnect);
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js");
    return () => { window.removeEventListener("online", reconnect); window.removeEventListener("offline", disconnect); };
  }, [activeMemberId]);

  const updatePlan = (key: string, value: string) => { const next = { ...plan, [key]: value }; setPlan(next); localStorage.setItem("threef-plan-draft", JSON.stringify(next)); };
  const updateRead = (key: string, value: string) => { const next = { ...read, [key]: value }; setRead(next); localStorage.setItem("threef-read-draft", JSON.stringify(next)); };
  const deliver = async (item: OutboxItem, success: string, destination: "anvil" | "plan" | "calibration") => {
    try { await send(item); setNotice(success); refresh(); setScreen(destination); } catch { queue(item); setNotice("Saved offline. It will synchronize when you reconnect."); setScreen(destination); }
  };
  const submitPlan = () => {
    const body = { command_id: commandId(), member_id: activeMemberId, season_name: plan.season_name, review_day: plan.review_day, review_time: plan.review_time, timezone: plan.timezone, roles: split(plan.roles), values: split(plan.values), domains: [{ name: plan.domain, current_reality: plan.current_reality, outcome: plan.outcome, protected_time: plan.protected_time, action: plan.action, boundary: plan.boundary, evidence: plan.evidence, weekly_actions: split(plan.weekly_actions), scoreboard_measure: plan.scoreboard_measure }], eliminations: [{ action: plan.elimination_action, commitment: plan.elimination }] };
    void deliver({ id: body.command_id, endpoint: "/api/season-plans", body }, "Season Plan submitted for Coach review.", "anvil");
  };
  const submitCalibration = () => {
    const strikes = [{ action: read.strike_one, measure: read.measure_one }, { action: read.strike_two, measure: read.measure_two }].filter((strike) => strike.action && strike.measure);
    const body = { command_id: commandId(), member_id: activeMemberId, week: dashboard?.current_week ?? 1, aim: read.aim, momentum_level: read.momentum_level, momentum_evidence: read.momentum_evidence, meaningful_moment: read.meaningful_moment, why_it_mattered: read.why_it_mattered, value_in_focus: read.value_in_focus, value_most_neglected: read.value_most_neglected, role_reads: [{ role: read.role, level: read.responsibility_level, evidence: read.responsibility_evidence }], avoided: read.avoided, drain: read.drain, unreleased_weight: read.unreleased_weight, role_to_forge: read.role_to_forge, strikes, scoreboard: { [plan.domain]: "green" } };
    void deliver({ id: body.command_id, endpoint: "/api/calibrations", body }, "Your calibration is recorded. Protect the next strike.", "anvil");
  };

  const planRoles = split(plan.roles);
  const planValues = split(plan.values);
  const isParticipant = dashboard?.role === "participant";
  const switchAccount = (memberId: string) => { localStorage.setItem("threef-development-account", memberId); setActiveMemberId(memberId); setScreen("anvil"); setNotice(""); };
  const planSteps: DeckStep[] = [
    { section: "The season", prompt: "What will you call this 12-week season?", hint: "Choose a name for the kind of man you are becoming.", content: <label>Season name<Field value={plan.season_name} onChange={(value) => updatePlan("season_name", value)} /></label> },
    { section: "Your stewardship", prompt: "Which roles are you carrying this season?", hint: "Choose the roles that need your deliberate attention. Select all that apply.", content: <ChipPicker options={ROLE_OPTIONS} selected={split(plan.roles)} onChange={(selected) => updatePlan("roles", selected.join(", "))} /> },
    { section: "Your stewardship", prompt: "Which values will you protect under pressure?", hint: "Choose the standards you intend to live, not an idealized version of yourself.", content: <ChipPicker options={VALUE_OPTIONS} selected={split(plan.values)} onChange={(selected) => updatePlan("values", selected.join(", "))} /> },
    { section: "Current reality", prompt: "What life domain needs intentional stewardship?", hint: "Start with one. State what is true without shame or exaggeration.", content: <><label>Domain<Field value={plan.domain} onChange={(value) => updatePlan("domain", value)} /></label><label>Right now, this area is...<Field multiline value={plan.current_reality} onChange={(value) => updatePlan("current_reality", value)} /></label></> },
    { section: "The outcome", prompt: "What will meaningful advancement look like?", hint: "Make the 12-week outcome realistic and measurable.", content: <label>By the end of this 12-week season, I will have...<Field multiline value={plan.outcome} onChange={(value) => updatePlan("outcome", value)} /></label> },
    { section: "The container", prompt: "What structure will protect this work?", hint: "Time, action, boundary, and proof. A container has to be repeatable.", content: <><label>Protected time<Field value={plan.protected_time} onChange={(value) => updatePlan("protected_time", value)} /></label><label>Action<Field value={plan.action} onChange={(value) => updatePlan("action", value)} /></label><label>Boundary<Field value={plan.boundary} onChange={(value) => updatePlan("boundary", value)} /></label><label>Evidence it works<Field value={plan.evidence} onChange={(value) => updatePlan("evidence", value)} /></label></> },
    { section: "Clear the load", prompt: "What will you remove so this season can hold?", hint: "A plan built on an overloaded life will not hold.", content: <><label>Weekly action<Field value={plan.weekly_actions} onChange={(value) => updatePlan("weekly_actions", value)} /></label><label>Scoreboard measure<Field value={plan.scoreboard_measure} onChange={(value) => updatePlan("scoreboard_measure", value)} /></label><label>Pause, delegate, finish, drop, or reduce<select value={plan.elimination_action} onChange={(event) => updatePlan("elimination_action", event.target.value)}><option value="pause">Pause</option><option value="delegate">Delegate</option><option value="finish">Finish</option><option value="drop">Drop</option><option value="reduce">Reduce</option></select></label><label>What commitment will you change?<Field value={plan.elimination} onChange={(value) => updatePlan("elimination", value)} /></label></> },
  ];
  const calibrationSteps: DeckStep[] = [
    { section: "1. Aim · The Furnace Stack", prompt: "What direction are you choosing to hold?", hint: "Your aim is the structure your life burns inside of.", content: <label>My current aim<Field multiline value={read.aim} onChange={(value) => updateRead("aim", value)} /></label> },
    { section: "1. Aim · Furnace Read", prompt: "How clean is your fire burning?", hint: "This measures internal flow versus buildup, not speed or output.", content: <><DiagnosticSlider title="Furnace read" lowLabel="Clogged" highLabel="Clean-Burning" value={read.momentum_level} items={momentum} onChange={(value) => updateRead("momentum_level", value)} /><label>What specifically created that level this week?<Field multiline value={read.momentum_evidence} onChange={(value) => updateRead("momentum_evidence", value)} placeholder="Name the evidence plainly." /></label></> },
    { section: "2. Meaning · The Hearth", prompt: "What moment carried weight?", hint: "If nothing stands out, name where you felt numb, distracted, or disconnected.", content: <><label>What happened?<Field multiline value={read.meaningful_moment} onChange={(value) => updateRead("meaningful_moment", value)} /></label><label>Why did it matter?<Field multiline value={read.why_it_mattered} onChange={(value) => updateRead("why_it_mattered", value)} /></label></> },
    { section: "3. Values · The Refractory Lining", prompt: "Which value was most in focus this week?", hint: "Choose from the values you named in your Season Plan.", content: <ChoicePicker options={planValues} value={read.value_in_focus} onChange={(value) => updateRead("value_in_focus", value)} /> },
    { section: "3. Values · The Refractory Lining", prompt: "Which value was most neglected this week?", hint: "Choose the one that received the least protection under pressure.", content: <ChoicePicker options={planValues} value={read.value_most_neglected} onChange={(value) => updateRead("value_most_neglected", value)} /> },
    { section: "4. Responsibility · The Anvil", prompt: "How stable were you under the weight?", hint: "No stories. Just weight and truth.", content: <><label>Role<Field value={read.role} onChange={(value) => updateRead("role", value)} /></label><DiagnosticSlider title="Forge read" lowLabel="Crushed" highLabel="Unbreakable" value={read.responsibility_level} items={responsibility} onChange={(value) => updateRead("responsibility_level", value)} /><label>What actually happened that justifies this rating?<Field multiline value={read.responsibility_evidence} onChange={(value) => updateRead("responsibility_evidence", value)} /></label></> },
    { section: "5. Friction · The Slag Channel", prompt: "What is clogging the system?", hint: "Do not fix it yet. Expose it clearly.", content: <><label>What did you avoid?<Field multiline value={read.avoided} onChange={(value) => updateRead("avoided", value)} /></label><label>What drained you?<Field multiline value={read.drain} onChange={(value) => updateRead("drain", value)} /></label><label>What are you still carrying?<Field multiline value={read.unreleased_weight} onChange={(value) => updateRead("unreleased_weight", value)} /></label></> },
    { section: "6. Cultivation · The Hammer", prompt: "Which role will you forge next?", hint: "Choose one of the roles you named in your Season Plan.", content: <ChoicePicker options={planRoles} value={read.role_to_forge} onChange={(value) => updateRead("role_to_forge", value)} /> },
    { section: "6. Cultivation · The Hammer", prompt: "What are your deliberate strikes?", hint: "Focused, measurable strikes beat intensity. Keep it to one or two.", content: <><label>First strike<Field value={read.strike_one} onChange={(value) => updateRead("strike_one", value)} /></label><label>How will you measure it?<Field value={read.measure_one} onChange={(value) => updateRead("measure_one", value)} /></label><label>Second strike, if needed<Field value={read.strike_two} onChange={(value) => updateRead("strike_two", value)} /></label><label>How will you measure it?<Field value={read.measure_two} onChange={(value) => updateRead("measure_two", value)} /></label></> },
  ];

  return <main>
    <header><div className="brand"><span className="mark">3F</span><div><strong>Clean Burn</strong><small>Read. Tell the truth. Strike.</small></div></div><div className={`connection ${online ? "online" : "offline"}`}>{online ? "Online" : "Offline"}</div></header>
    {DEVELOPMENT_MODE && accounts.length > 0 && <label className="account-switcher"><span>Development account</span><select value={activeMemberId} onChange={(event) => switchAccount(event.target.value)}>{accounts.map((account) => <option value={account.member_id} key={account.member_id}>{account.name} · {account.role}</option>)}</select></label>}
    <nav><button className={screen === "anvil" ? "active" : ""} onClick={() => setScreen("anvil")}>Anvil</button>{isParticipant && <button className={screen === "plan" ? "active" : ""} onClick={() => setScreen("plan")}>Season Plan</button>}{isParticipant && <button className={screen === "calibration" ? "active" : ""} onClick={() => setScreen("calibration")}>Weekly Calibration</button>}</nav>
    {notice && <aside className="notice">{notice}</aside>}
    {screen === "anvil" && <section className="home"><p className="eyebrow">{dashboard?.role ?? "Account"} · {dashboard?.season_plan?.season_name ?? "The Stewardship Season"}</p><h1>{dashboard ? `The Anvil, ${dashboard.name}.` : "The Anvil."}</h1><p className="lead">{isParticipant ? "A clear read on what you are feeding, holding, and releasing." : "A development view of the people and responsibilities entrusted to you."}</p>{isParticipant ? <><div className="cards"><article><span>Current week</span><strong>{dashboard?.current_week ?? 1} / 12</strong><p>{dashboard?.calibration_count ?? 0} calibrations recorded</p></article><article><span>Coach</span><strong>{dashboard?.coach_name ?? "Loading..."}</strong><p>{dashboard?.latest_review ? "Latest feedback is ready" : "Your witness in the work"}</p></article><article><span>Next strike</span><strong>{dashboard?.latest_calibration?.strikes?.[0]?.action ?? "Build your Season Plan"}</strong><p>{dashboard?.latest_calibration?.role_to_forge ? `Forge: ${dashboard.latest_calibration.role_to_forge}` : "Start with stewardship"}</p></article></div>{dashboard?.latest_calibration && <article className="read-summary"><p className="eyebrow">Last calibration</p><h2>{dashboard.latest_calibration.aim}</h2><p>Furnace read: <b>{dashboard.latest_calibration.momentum_level.replace("_", " ")}</b></p>{dashboard.latest_review && <blockquote>{dashboard.latest_review.feedback}</blockquote>}</article>}<button className="primary" onClick={() => setScreen(dashboard?.season_plan ? "calibration" : "plan")}>{dashboard?.season_plan ? "Begin weekly calibration" : "Build the season plan"}</button></> : <><div className="cards"><article><span>Role</span><strong>{dashboard?.role}</strong><p>Development account view</p></article><article><span>Direct reports</span><strong>{dashboard?.direct_reports.length ?? 0}</strong><p>{dashboard?.role === "coach" ? "Participants assigned to you" : "Coaches assigned to you"}</p></article></div><section className="report-list"><p className="eyebrow">Your people</p>{dashboard?.direct_reports.length ? dashboard.direct_reports.map((report) => <article key={report.member_id}><strong>{report.name}</strong><span>{report.role}</span></article>) : <p className="lead">No direct reports are assigned yet.</p>}</section></>}</section>}
    {screen === "plan" && <Deck eyebrow="Season Plan" steps={planSteps} submitLabel="Submit season plan" onSubmit={submitPlan} />}
    {screen === "calibration" && <Deck eyebrow={`Week ${dashboard?.current_week ?? 1} · Weekly Calibration`} steps={calibrationSteps} submitLabel="Submit calibration" onSubmit={submitCalibration} />}
  </main>;
}

createRoot(document.getElementById("root")!).render(<App />);
