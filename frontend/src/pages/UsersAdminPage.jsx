import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import {
  createCollaborator,
  listAreas,
  listLevels,
  listUsers,
  updateUserLevel,
  updateUserStatus,
} from "../api/usersApi";

function UsersAdminPage() {
  const [users, setUsers] = useState([]);
  const [areas, setAreas] = useState([]);
  const [levels, setLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    area_id: "",
    access_level_code: 4,
  });

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [usersData, areasData, levelsData] = await Promise.all([
        listUsers(),
        listAreas(),
        listLevels(),
      ]);
      setUsers(usersData);
      setAreas(areasData);
      setLevels(levelsData);
      if (!form.area_id && areasData.length > 0) {
        setForm((current) => ({ ...current, area_id: String(areasData[0].id) }));
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "No fue posible cargar usuarios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload = {
        full_name: form.full_name,
        email: form.email,
        area_id: Number(form.area_id),
        access_level_code: Number(form.access_level_code),
      };
      const result = await createCollaborator(payload);
      const linkMessage = result.activation_link
        ? ` Enlace de activación (demo): ${result.activation_link}`
        : " Enlace enviado por SMTP.";
      setSuccess(`Colaborador creado correctamente.${linkMessage}`);
      setForm((current) => ({ ...current, full_name: "", email: "" }));
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo crear el colaborador");
    }
  };

  const handleChangeLevel = async (userId, levelCode, areaId) => {
    setError("");
    setSuccess("");
    try {
      await updateUserLevel(userId, {
        access_level_code: Number(levelCode),
        area_id: Number(areaId),
      });
      setSuccess("Nivel de acceso actualizado.");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo actualizar el nivel");
    }
  };

  const handleToggleStatus = async (userId, nextStatus) => {
    if (!nextStatus) {
      const confirmed = window.confirm("¿Desactivar este usuario? Perderá acceso al sistema.");
      if (!confirmed) return;
    }
    setError("");
    setSuccess("");
    try {
      await updateUserStatus(userId, nextStatus);
      setSuccess("Estado actualizado.");
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo actualizar el estado");
    }
  };

  return (
    <main className="container">
      <AppNav />

      <section className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>Alta de colaborador</h2>
        <form className="grid" onSubmit={handleCreate}>
          <input
            className="input"
            type="text"
            placeholder="Nombre completo"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            required
          />
          <input
            className="input"
            type="email"
            placeholder="Correo"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
          <select
            className="select"
            value={form.area_id}
            onChange={(event) => setForm({ ...form, area_id: event.target.value })}
            required
          >
            {areas.map((area) => (
              <option key={area.id} value={area.id}>
                {area.name}
              </option>
            ))}
          </select>
          <select
            className="select"
            value={form.access_level_code}
            onChange={(event) => setForm({ ...form, access_level_code: event.target.value })}
            required
          >
            {levels.map((level) => (
              <option key={level.code} value={level.code}>
                {level.name}
              </option>
            ))}
          </select>
          <button className="button" type="submit">
            Crear colaborador
          </button>
        </form>
        {success ? <p className="success">{success}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Usuarios</h2>
        {loading ? <p>Cargando...</p> : null}

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Área</th>
                <th>Nivel</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{user.area_name || "Sin área"}</td>
                  <td>
                    <select
                      className="select"
                      value={user.access_level_code}
                      onChange={(event) =>
                        handleChangeLevel(user.id, event.target.value, user.area_id ?? Number(form.area_id))
                      }
                    >
                      {levels.map((level) => (
                        <option key={level.code} value={level.code}>
                          {level.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <span className={`status ${user.is_active ? "active" : "inactive"}`}>
                      {user.status}
                    </span>
                  </td>
                  <td>
                    {user.is_active ? (
                      <button
                        className="button warning"
                        type="button"
                        onClick={() => handleToggleStatus(user.id, false)}
                      >
                        Desactivar
                      </button>
                    ) : (
                      <button
                        className="button"
                        type="button"
                        onClick={() => handleToggleStatus(user.id, true)}
                      >
                        Reactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default UsersAdminPage;
