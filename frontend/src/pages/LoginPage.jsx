import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "No fue posible iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container" style={{ maxWidth: 440 }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Ingreso</h1>
        <p>Demo de gestión de identidades y control de acceso por niveles.</p>
        <form onSubmit={onSubmit}>
          <label htmlFor="email">Correo</label>
          <input
            id="email"
            type="email"
            className="input"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />

          <label htmlFor="password" style={{ marginTop: 10, display: "block" }}>
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            className="input"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            required
          />

          <button className="button" type="submit" style={{ marginTop: 14 }} disabled={loading}>
            {loading ? "Ingresando..." : "Entrar"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </div>
    </main>
  );
}

export default LoginPage;
