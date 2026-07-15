import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar.jsx";
import TopBar from "../components/TopBar.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import Composer from "../components/Composer.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { useChat } from "../hooks/useChat.js";
import { useSessions } from "../hooks/useSessions.js";
import "./ChatPage.css";

export default function ChatPage() {
  const { token } = useAuth();
  const { sessions, refresh } = useSessions(token);
  const { sessionId, messages, isTyping, sendMessage, startNewConversation, loadConversation } =
    useChat(token, { onConversationUpdated: refresh });

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      const list = await refresh();
      if (!cancelled && list.length) {
        loadConversation(list[0].session_id);
      }
    }
    if (token) init();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="chat-page">
      <Sidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={loadConversation}
        onNewConversation={startNewConversation}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />
      <div className="chat-page__main">
        <TopBar />
        <ChatWindow messages={messages} isTyping={isTyping} />
        <Composer onSend={sendMessage} disabled={isTyping} />
      </div>
    </div>
  );
}
