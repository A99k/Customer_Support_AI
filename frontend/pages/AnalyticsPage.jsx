import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { useAnalytics } from "../hooks/useAnalytics.js";
import "./AnalyticsPage.css";

const CHART_COLORS = ["#10a37f", "#f0a72e", "#7fb3ff", "#f2879a", "#b29cff", "#8e8ea0"];

function toChartArray(obj = {}) {
  return Object.entries(obj).map(([name, value]) => ({ name, value }));
}

export default function AnalyticsPage() {
  const { token } = useAuth();
  const { data, loading, error, load } = useAnalytics(token, { scope: "admin" });
  const [days, setDays] = useState(14);

  useEffect(() => {
    load(days);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const intentData = toChartArray(data?.intent_counts);
  const agentData = toChartArray(data?.agent_counts);

  return (
    <div className="analytics-page">
      <header className="analytics-header">
        <div className="analytics-brand">
          <div className="analytics-mark">TM</div>
          <div>
            <h1>Support Analytics</h1>
            <p>Cross-agent performance, routing, and escalation signal</p>
          </div>
        </div>
        <div className="analytics-controls">
          <div className="range-toggle">
            {[7, 14, 30].map((d) => (
              <button key={d} className={d === days ? "active" : ""} onClick={() => setDays(d)}>
                {d}d
              </button>
            ))}
          </div>
          <Link to="/" className="back-link">
            ← Back to chat
          </Link>
        </div>
      </header>

      {error && <div className="analytics-error">{error}</div>}
      {loading && !data && <div className="analytics-loading">Loading analytics…</div>}

      {data && (
        <>
          <div className="stat-grid">
            <StatCard label="Conversations" value={data.total_conversations} />
            <StatCard label="Messages" value={data.total_messages} />
            <StatCard label="Customers" value={data.total_users} />
            <StatCard label="Avg. msgs / conversation" value={data.avg_messages_per_conversation} />
            <StatCard
              label="Escalation rate"
              value={`${Math.round(data.escalation_rate * 100)}%`}
              accent="warn"
            />
          </div>

          <div className="panel">
            <h3>Messages over time</h3>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={data.messages_by_day}>
                <CartesianGrid stroke="#2f2f2f" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => d.slice(5)}
                  stroke="#8e8ea0"
                  fontSize={11}
                />
                <YAxis stroke="#8e8ea0" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #2f2f2f", fontSize: 12 }}
                  labelStyle={{ color: "#ececec" }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#10a37f"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Messages"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid-2">
            <div className="panel">
              <h3>
                Intent <span className="accent">distribution</span>
              </h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={intentData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid stroke="#2f2f2f" horizontal={false} />
                  <XAxis type="number" stroke="#8e8ea0" fontSize={11} allowDecimals={false} />
                  <YAxis dataKey="name" type="category" stroke="#ececec" fontSize={12} width={80} />
                  <Tooltip contentStyle={{ background: "#1a1a1a", border: "1px solid #2f2f2f", fontSize: 12 }} />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                    {intentData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="panel">
              <h3>
                Agent <span className="accent">routing</span>
              </h3>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={agentData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                    {agentData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#1a1a1a", border: "1px solid #2f2f2f", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="legend">
                {agentData.map((d, i) => (
                  <div key={d.name} className="legend__item">
                    <span
                      className="legend__swatch"
                      style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                    />
                    {d.name}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>Recent escalations</h3>
            <div className="escalation-list">
              {data.recent_escalations.length === 0 && (
                <div className="empty-state">No escalations in this window.</div>
              )}
              {data.recent_escalations.map((esc) => (
                <div key={`${esc.session_id}-${esc.timestamp}`} className="escalation-item">
                  <div className="escalation-item__meta">
                    {esc.session_id.slice(0, 8)} · {new Date(esc.timestamp).toLocaleString()}
                  </div>
                  <div className="escalation-item__msg">{esc.message}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div className="stat-card">
      <div className="stat-card__label">{label}</div>
      <div className={"stat-card__value" + (accent ? ` stat-card__value--${accent}` : "")}>{value}</div>
    </div>
  );
}
