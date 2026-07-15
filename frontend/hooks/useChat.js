import { useCallback, useState } from "react";
import * as chatService from "../services/chatService.js";
import * as sessionService from "../services/sessionService.js";

const GREETING = {
  role: "assistant",
  content:
    "Hi, I'm the TechMart support assistant. Ask me about orders, billing, technical issues, products, or anything else — I'll route you to the right specialist.",
  agentsUsed: [],
  escalated: false,
};

export function useChat(token, { onConversationUpdated } = {}) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([GREETING]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);

  const startNewConversation = useCallback(() => {
    setSessionId(null);
    setMessages([GREETING]);
    setError(null);
  }, []);

  const loadConversation = useCallback(
    async (id) => {
      setSessionId(id);
      setError(null);
      try {
        const data = await sessionService.getHistory(token, id);
        if (!data.turns.length) {
          setMessages([GREETING]);
          return;
        }
        setMessages(
          data.turns.map((t) => ({
            role: t.role,
            content: t.content,
            agentsUsed: t.agents_used || [],
            escalated: Boolean(t.escalated),
          }))
        );
      } catch (err) {
        setError(err.message || "Couldn't load that conversation.");
      }
    },
    [token]
  );

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setIsTyping(true);
      setError(null);

      try {
        let activeSessionId = sessionId;
        if (!activeSessionId) {
          const created = await sessionService.createSession(token);
          activeSessionId = created.session_id;
          setSessionId(activeSessionId);
        }

        const data = await chatService.sendChatMessage(token, {
          sessionId: activeSessionId,
          message: trimmed,
        });

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.reply,
            agentsUsed: data.agents_used,
            escalated: data.escalated,
          },
        ]);

        if (onConversationUpdated) onConversationUpdated();
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              err.name === "AuthError"
                ? "Your session has expired. Please log in again."
                : "I couldn't reach the support backend. Make sure it's running and try again.",
          },
        ]);
        setError(err);
      } finally {
        setIsTyping(false);
      }
    },
    [sessionId, token, onConversationUpdated]
  );

  return {
    sessionId,
    messages,
    isTyping,
    error,
    sendMessage,
    startNewConversation,
    loadConversation,
  };
}
