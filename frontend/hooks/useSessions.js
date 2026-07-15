import { useCallback, useState } from "react";
import * as sessionService from "../services/sessionService.js";

export function useSessions(token) {
  const [sessions, setSessions] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return [];
    const data = await sessionService.listSessions(token);
    setSessions(data.sessions);
    setLoaded(true);
    return data.sessions;
  }, [token]);

  return { sessions, refresh, loaded };
}
