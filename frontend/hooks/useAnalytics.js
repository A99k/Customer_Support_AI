import { useCallback, useState } from "react";
import * as analyticsService from "../services/analyticsService.js";

export function useAnalytics(token, { scope = "admin" } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(
    async (days = 14) => {
      setLoading(true);
      setError(null);
      try {
        const result =
          scope === "admin"
            ? await analyticsService.fetchAnalyticsSummary(token, days)
            : await analyticsService.fetchMyAnalytics(token, days);
        setData(result);
      } catch (err) {
        setError(err.message || "Failed to load analytics.");
      } finally {
        setLoading(false);
      }
    },
    [token, scope]
  );

  return { data, loading, error, load };
}
