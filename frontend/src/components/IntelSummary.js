import React, { useMemo } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import {
  Layers, AlarmClock, Sparkles, DollarSign, Radio, Flag, ShieldAlert, TrendingUp,
} from "lucide-react";
import { Card, SectionLabel, Pill } from "./ui";
import { fmtMoney, CHART_SERIES } from "../lib/helpers";
import { countBy, upcoming, topValue, moneyColor } from "../lib/intel";

const tip = { background: "var(--bg-elev)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)", fontSize: 12 };

function Kpi({ icon: Icon, label, value, tone = "cyan", alert }) {
  return (
    <Card hover className="p-4" data-testid={`intel-kpi-${label.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="flex items-start justify-between">
        <SectionLabel>{label}</SectionLabel>
        <Icon size={16} className={alert ? "text-bad" : `text-${tone}`} />
      </div>
      <div className={`mono mt-2 text-2xl font-semibold ${alert ? "text-bad" : "text-ink"}`}>{value}</div>
    </Card>
  );
}

export default function IntelSummary({ report }) {
  const opps = useMemo(() => report?.opportunities || [], [report]);
  const es = report?.executiveSummary || {};
  const byMission = useMemo(() => countBy(opps, "missionCategory").slice(0, 10), [opps]);
  const byAgency = useMemo(() => countBy(opps, "agency").slice(0, 10), [opps]);
  const byVehicle = useMemo(() => countBy(opps, "vehicle").slice(0, 8), [opps]);
  const byMoney = useMemo(() => countBy(opps, "colorOfMoney"), [opps]);
  const soon = useMemo(() => upcoming(opps, 14), [opps]);
  const top = useMemo(() => topValue(opps, 5), [opps]);
  const excellent = opps.filter((o) => (Number(o.fitScore) || 0) >= 90).length;
  const maxAward = opps.reduce((m, o) => Math.max(m, Number(o.awardAmount) || 0), 0);

  return (
    <div className="space-y-5" data-testid="intel-summary">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi icon={Layers} label="Opportunities" value={opps.length} />
        <Kpi icon={AlarmClock} label="Due ≤ 14 Days" value={soon.length} alert={soon.length > 0} />
        <Kpi icon={Sparkles} label="Excellent Fit" value={excellent} tone="ok" />
        <Kpi icon={DollarSign} label="Top Award" value={fmtMoney(maxAward)} tone="violet" />
      </div>

      {es.narrative && (
        <Card className="p-5">
          <div className="flex items-center gap-2"><TrendingUp size={15} className="text-cyan" /><SectionLabel>Executive Read</SectionLabel></div>
          <p className="mt-2 text-sm text-dim">{es.narrative}</p>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <SectionLabel>By Mission Category</SectionLabel>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byMission} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" horizontal={false} />
                <XAxis type="number" tick={{ fill: "var(--text-faint)", fontSize: 11 }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: "var(--text-dim)", fontSize: 10 }} width={130} />
                <Tooltip contentStyle={tip} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#38e1ff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <SectionLabel>By Agency (Top 10)</SectionLabel>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byAgency} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" horizontal={false} />
                <XAxis type="number" tick={{ fill: "var(--text-faint)", fontSize: 11 }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: "var(--text-dim)", fontSize: 10 }} width={130} />
                <Tooltip contentStyle={tip} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#8b7bff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <SectionLabel>By Contract Vehicle</SectionLabel>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byVehicle} dataKey="value" nameKey="name" innerRadius={48} outerRadius={84} paddingAngle={2}>
                  {byVehicle.map((d, i) => <Cell key={d.name} fill={CHART_SERIES[i % CHART_SERIES.length]} stroke="var(--bg-panel)" />)}
                </Pie>
                <Tooltip contentStyle={tip} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap gap-2">
              {byVehicle.map((d, i) => (
                <span key={d.name} className="flex items-center gap-1 text-xs text-faint">
                  <i className="h-2 w-2 rounded-full" style={{ background: CHART_SERIES[i % CHART_SERIES.length] }} /> {d.name} ({d.value})
                </span>
              ))}
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <SectionLabel>By Color of Money</SectionLabel>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byMoney} dataKey="value" nameKey="name" innerRadius={48} outerRadius={84} paddingAngle={2}>
                  {byMoney.map((d) => <Cell key={d.name} fill={moneyColor(d.name)} stroke="var(--bg-panel)" />)}
                </Pie>
                <Tooltip contentStyle={tip} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap gap-2">
              {byMoney.map((d) => (
                <span key={d.name} className="flex items-center gap-1 text-xs text-faint">
                  <i className="h-2 w-2 rounded-full" style={{ background: moneyColor(d.name) }} /> {d.name} ({d.value})
                </span>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center gap-2"><AlarmClock size={15} className="text-bad" /><SectionLabel>Upcoming Deadlines (14 days)</SectionLabel></div>
          {soon.length === 0 ? <p className="mt-3 text-sm text-faint">No deadlines inside 14 days.</p> : (
            <ul className="mt-3 space-y-2">
              {soon.slice(0, 8).map((o, i) => (
                <li key={i} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-dim">{o.title}</span>
                  <Pill tone="bad">{o._d}d</Pill>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2"><DollarSign size={15} className="text-violet" /><SectionLabel>Highest-Value Opportunities</SectionLabel></div>
          {top.length === 0 ? <p className="mt-3 text-sm text-faint">No award ceilings reported.</p> : (
            <ul className="mt-3 space-y-2">
              {top.map((o, i) => (
                <li key={i} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-dim">{o.title}</span>
                  <span className="mono text-violet">{fmtMoney(o._a)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {(es.hotSignals || []).length > 0 && (
          <Card className="p-5">
            <div className="flex items-center gap-2"><Radio size={15} className="text-cyan" /><SectionLabel>Hot Signals / BD Intel</SectionLabel></div>
            <ul className="mt-3 space-y-2">
              {(es.hotSignals || []).map((s, i) => (
                <li key={i} className="text-sm text-dim">
                  • {s.signal || s}{s.source ? <span className="text-faint"> — {s.source}</span> : null}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {(es.recommendedActions || []).length > 0 && (
          <Card className="p-5">
            <div className="flex items-center gap-2"><Flag size={15} className="text-ok" /><SectionLabel>Recommended Actions</SectionLabel></div>
            <ul className="mt-3 space-y-2">
              {(es.recommendedActions || []).map((a, i) => (
                <li key={i} className="flex gap-2 text-sm text-dim"><span className="mono text-ok">{i + 1}.</span> {a}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {(report?.sourceStatus || []).length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2"><ShieldAlert size={15} className="text-warn" /><SectionLabel>Source Status</SectionLabel></div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(report.sourceStatus || []).map((s, i) => (
              <Pill key={i} tone={(s.status || "").includes("reach") ? "ok" : "neutral"} title={s.note || ""}>
                {s.source}: {s.status}
              </Pill>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
