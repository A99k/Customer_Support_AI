import React from "react";
import RoutingBadges from "./RoutingBadges.jsx";
import "./MessageBubble.css";

export default function MessageBubble({ role, content, agentsUsed, escalated }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="msg-row msg-row--user">
        <div className="user-bubble">{content}</div>
      </div>
    );
  }

  return (
    <div className={"msg-row msg-row--assistant" + (escalated ? " msg-row--escalated" : "")}>
      <div className="avatar avatar--assistant">TM</div>
      <div className="assistant-content">
        <div className="assistant-text">{content}</div>
        <RoutingBadges agentsUsed={agentsUsed} escalated={escalated} />
      </div>
    </div>
  );
}
