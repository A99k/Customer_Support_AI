import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import "./Sidebar.css";

function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewConversation,
  collapsed,
  onToggleCollapse,
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className={"sidebar" + (collapsed ? " sidebar--collapsed" : "")}>
      <div className="sidebar__top">
        <button
          className="icon-btn sidebar__collapse-btn"
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.6" />
            <line x1="9.5" y1="4" x2="9.5" y2="20" stroke="currentColor" strokeWidth="1.6" />
          </svg>
        </button>
        {!collapsed && (
          <button className="new-chat-btn" onClick={onNewConversation}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
            New conversation
          </button>
        )}
      </div>

      {!collapsed && (
        <>
          <div className="sidebar__section-label">Conversations</div>
          <div className="conversation-list">
            {sessions.length === 0 && (
              <div className="sidebar-empty">No conversations yet — send a message to start one.</div>
            )}
            {sessions.map((s) => (
              <button
                key={s.session_id}
                className={"conv-item" + (s.session_id === activeSessionId ? " conv-item--active" : "")}
                onClick={() => onSelectSession(s.session_id)}
              >
                <div className="conv-item__preview">{s.preview}</div>
                <div className="conv-item__meta">
                  {s.message_count} msg · {timeAgo(s.last_activity)}
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      <div className="sidebar__bottom">
        {!collapsed && user?.is_admin && (
          <Link to="/analytics" className="sidebar__link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M4 19V10M10 19V5M16 19V13M22 19H2"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            Analytics
          </Link>
        )}
        <div className="sidebar__user">
          <div className="sidebar__user-avatar">{(user?.name || "?").charAt(0).toUpperCase()}</div>
          {!collapsed && (
            <div className="sidebar__user-info">
              <div className="sidebar__user-name">{user?.name}</div>
              <button className="sidebar__logout" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
