import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from "recharts";
import {
  Activity, DollarSign, AlarmClock, Trophy, Inbox, Target,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Skeleton, EmptyState, PageReveal } from "../components/ui";
import { fmtMoney, daysUntil, STAGE_COLORS, CHART_SERIES } from "../lib/helpers";

const STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"];
const tooltipStyle = {
  background: "var(--bg-elev)", border: "1px solid var(--line)",
  borderRadius: 10, color: "var(--text)", fontSize: 12,
};

function Kpi({ icon: Icon, label, value, tone = "cyan", alert, sub }) {
  return (
    <Card hover className="p-5" data-testid={`kpi-${label.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="flex items-start justify-between">
        <SectionLabel>{label}</SectionLabel>
        <Icon size={18} className={alert ? "text-bad" : `text-${tone}`} />
      </div>
      <div className={`mono mt-3 text-3xl font-semibold ${alert ? "text-bad" : "text-ink"}`}>
        {value}
      </div>
      {sub && <div className="mt-1 text-xs text-faint">{sub}</div>}
    </Card>
  );
}

export default function Dashboard() {
  const { activeOrgId, activeOrg } = useAuth();
  const navigate = useNavigate();
  const [opps, setOpps] = useState(null);
  const [pieMode, setPieMode] = useState("setAside");

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities`)
      .then((r) => setOpps(r.data))
      .catch((e) => { errMsg(e); setOpps([]); });
  }, [activeOrgId]);

  const kpis = useMemo(() => {
    if (!opps) return null;
    const active = opps.filter((o) => !["Won", "Lost", "No-Bid"].includes(o.stage));
    const ceiling = active.reduce((s, o) => s + (Number(o.ceiling) || 0), 0);
    const dueSoon = opps.filter((o) => {
      const d = daysUntil(o.dueDate);
      return d != null && d >= 0 && d <= 7;
    }).length;
    const won = opps.filter((o) => o.stage === "Won").length;
    const lost = opps.filter((o) => ["Lost", "No-Bid"].includes(o.stage)).length;
    return { active: active.length, ceiling, dueSoon, won, lost };
  }, [opps]);

  const stageData = useMemo(() => {
    if (!opps) return [];
    return STAGES.map((s) => ({ stage: s, count: opps.filter((o) => o.stage === s).length }));
  }, [opps]);

  const pieData = useMemo(() => {
    if (!opps) return [];
    const map = {};
    opps.forEach((o) => {
      const key = (pieMode === "setAside" ? o.setAside : o.vehicle) || "Unknown";
      map[key] = (map[key] || 0) + (Number(o.ceiling) || 0);
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [opps, pieMode]);

  const lineData = useMemo(() => {
    if (!opps) return [];
    const months = {};
    const now = new Date();
    for (let i = 0; i < 9; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
      const k = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
      months[k] = { month: k, identified: 0, submitted: 0 };
    }
    opps.forEach((o) => {
      if (!o.dueDate) return;
      const d = new Date(o.dueDate);
      if (isNaN(d)) return;
      const k = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
      if (months[k]) {
        if (o.stage === "Submitted") months[k].submitted += 1;
        else months[k].identified += 1;
      }
    });
    return Object.values(months);
  }, [opps]);

  const agencyData = useMemo(() => {
    if (!opps) return [];
    const map = {};
    opps.forEach((o) => {
      const a = o.agency || "Unknown";
      map[a] = (map[a] || 0) + (Number(o.ceiling) || 0);
    });
    return Object.entries(map)
      .map(([name, value]) => ({ name: name.replace("Department of the ", "").replace("Department of ", ""), value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);
  }, [opps]);

  if (opps === null) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-72" /><Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const empty = opps.length === 0;

  return (
    <PageReveal className="space-y-6">
      <div>
        <SectionLabel>Mission Dashboard</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">{activeOrg?.name}</h1>
      </div>

      {empty ? (
        <Card className="p-6">
          <EmptyState
            icon={Inbox}
            title="No data yet"
            subtitle="Add opportunities manually or pull from SAM/Grants to populate your pipeline."
            action={
              <button className="btn btn-primary" onClick={() => navigate("/opportunities")} data-testid="empty-go-opps">
                <Target size={16} /> Go to Opportunities
              </button>
            }
          />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi icon={Activity} label="Active Pursuits" value={kpis.active} />
            <Kpi icon={DollarSign} label="Pipeline Ceiling" value={fmtMoney(kpis.ceiling)} tone="violet" />
            <Kpi icon={AlarmClock} label="Due ≤ 7 Days" value={kpis.dueSoon} alert={kpis.dueSoon > 0} />
            <Kpi icon={Trophy} label="Win / Loss FY" value={`${kpis.won} / ${kpis.lost}`} tone="ok" sub="Won vs Lost+No-Bid" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <SectionLabel>Opportunities by Stage</SectionLabel>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stageData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="stage" tick={{ fill: "var(--text-faint)", fontSize: 11 }} angle={-15} textAnchor="end" height={50} />
                    <YAxis tick={{ fill: "var(--text-faint)", fontSize: 11 }} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      {stageData.map((d) => <Cell key={d.stage} fill={STAGE_COLORS[d.stage]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between">
                <SectionLabel>Pipeline by {pieMode === "setAside" ? "Set-Aside" : "Vehicle"}</SectionLabel>
                <div className="flex gap-1">
                  {["setAside", "vehicle"].map((m) => (
                    <button key={m} onClick={() => setPieMode(m)}
                      className={`pill ${pieMode === m ? "border-cyan/50 bg-cyan/10 text-cyan" : "border-line text-faint"}`}
                      data-testid={`pie-toggle-${m}`}>
                      {m === "setAside" ? "Set-Aside" : "Vehicle"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                      {pieData.map((d, i) => <Cell key={d.name} fill={CHART_SERIES[i % CHART_SERIES.length]} stroke="var(--bg-panel)" />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtMoney(v)} />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-dim)" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-5">
              <SectionLabel>Closing by Month</SectionLabel>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={lineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fill: "var(--text-faint)", fontSize: 11 }} />
                    <YAxis tick={{ fill: "var(--text-faint)", fontSize: 11 }} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-dim)" }} />
                    <Line type="monotone" dataKey="identified" stroke="#38e1ff" strokeWidth={2} dot={{ r: 3 }} name="Identified" />
                    <Line type="monotone" dataKey="submitted" stroke="#fbbf24" strokeWidth={2} dot={{ r: 3 }} name="Submitted" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-5">
              <SectionLabel>Top Agencies by Ceiling</SectionLabel>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={agencyData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "var(--text-faint)", fontSize: 11 }} tickFormatter={fmtMoney} />
                    <YAxis type="category" dataKey="name" tick={{ fill: "var(--text-dim)", fontSize: 11 }} width={90} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtMoney(v)} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#8b7bff" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
    </PageReveal>
  );
}
