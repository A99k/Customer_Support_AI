import React from "react";
import "./RoutingBadges.css";

export default function RoutingBadges({ agentsUsed = [], escalated = false }) {
  if (!agentsUsed.length && !escalated) return null;

  return (
    <div className="routing-badges">
      {agentsUsed.map((agent) => (
        <span key={agent} className="badge">
          {agent}
        </span>
      ))}
      {escalated && <span className="badge badge--escalate">escalated</span>}
    </div>
  );
}
