import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import HealthStatus from "./components/HealthStatus";
import HighRiskAlerts from "./components/HighRiskAlerts";

// Placeholders for now
const Dashboard = () => (
  <>
    <h2>Staff Dashboard</h2>
    <HighRiskAlerts />
  </>
)
const CheckIn = () => <h2>Pitcher Daily Check-in</h2>

function RequireRole({ roles, children}) {
  const { user, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

// Checks user role and redirects to the appropriate page
function Home() {
  const { user, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "pitcher" ? "/check-in" : "/dashboard"} replace />;
}

// Main app component
export default function App() {
  const { user, logout } = useAuth();
  const location = useLocation();
  return (
    // Displays the health status of the API
    <>
    <h1>PitchIQ</h1>
    <HealthStatus />
    {user && (
      <p>
        Signed in as {user.username} ({user.role}) <button onClick={logout}>Log out</button>
      </p>
    )}
    {user && (user.role === "manager" || user.role === "admin") && location.pathname !== "/dashboard" && (
      <HighRiskAlerts compact />
    )}

    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<RequireRole roles={["manager", "admin"]}><Dashboard /></RequireRole>} />
      <Route path="/check-in" element={<RequireRole roles={["pitcher"]}><CheckIn /></RequireRole>} />
    </Routes>
    </>
  ) 
}