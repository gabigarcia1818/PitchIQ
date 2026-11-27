import { useEffect, useState } from "react";
import api from "../api/client";
import "./HighRiskAlerts.css";

function formatScore(score) {
  const value = Number(score);
  if (Number.isNaN(value)) return score;
  return value.toFixed(2);
}

export default function HighRiskAlerts({ compact = false }) {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/high-risk-alerts/")
      .then((response) => {
        if (!cancelled) setAlerts(response.data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load high-risk alerts.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return compact ? null : <p>Loading alerts...</p>;
  if (error) return <p className="high-risk-alerts-error">{error}</p>;
  if (!alerts.length) {
    return compact ? null : <p>No high-risk alerts.</p>;
  }

  if (compact) {
    const latest = alerts[0];
    const extra = alerts.length > 1 ? ` and ${alerts.length - 1} more` : "";
    return (
      <div className="high-risk-banner" role="status">
        High-risk alert: {latest.pitcher_username} scored {formatScore(latest.risk_score)}
        {latest.outing_date ? ` on ${latest.outing_date}` : ""}
        {extra}
      </div>
    );
  }

  return (
    <section className="high-risk-alerts">
      <h3>High-risk alerts</h3>
      <ul>
        {alerts.map((alert) => (
          <li key={alert.id} className="high-risk-banner">
            High-risk alert: {alert.pitcher_username} scored {formatScore(alert.risk_score)}
            {alert.outing_date ? ` on ${alert.outing_date}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
