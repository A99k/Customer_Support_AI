import React from "react";
import "./TypingIndicator.css";

export default function TypingIndicator() {
  return (
    <div className="typing-row">
      <div className="avatar avatar--assistant">TM</div>
      <div className="typing-dots" aria-label="Assistant is typing">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
