import { NavLink, useNavigate } from "react-router-dom";
import { STAFF, useAuth } from "../auth";

// The role name an investigator would recognise, rather than the database value.
const ROLE_LABELS = {
  CUSTOMER: "Customer",
  ANALYST: "Fraud investigator",
  COMPLIANCE: "Compliance officer",
  ADMIN: "System administrator",
};

const LINKS = [
  { to: "/", label: "Overview", roles: STAFF, end: true },
  { to: "/transactions", label: "Transactions", roles: ["CUSTOMER", ...STAFF] },
  { to: "/submit", label: "Submit a transaction", roles: ["CUSTOMER", ...STAFF] },
  { to: "/alerts", label: "Alert queue", roles: STAFF },
  { to: "/cases", label: "Cases", roles: STAFF },
  { to: "/admin", label: "Administration", roles: ["ADMIN", "COMPLIANCE"] },
  { to: "/aml-testing", label: "AML Testing", roles: ["ADMIN"] },
];

export default function Layout({ children }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function handleSignOut() {
    signOut();
    navigate("/login");
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div className="wordmark">
          FinShield AI
          <span>Financial crime console</span>
        </div>
        <nav>
          {LINKS.filter((link) => link.roles.includes(user.role)).map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-foot">
          <strong>{user.username}</strong>
          {ROLE_LABELS[user.role] || user.role}
          <button onClick={handleSignOut}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
