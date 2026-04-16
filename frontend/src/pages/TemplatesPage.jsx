import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import { listTemplates, createTemplate, updateTemplate, updateTemplateStatus } from "../api/templatesApi";

const FIELD_TYPES = ["text", "select", "multiselect", "textarea", "date", "number"];

function TemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fields, setFields] = useState([{ name: "", label: "", field_type: "text", required: false, options: [] }]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Error cargando plantillas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const clearMsg = () => { setError(""); setSuccess(""); };

  const resetForm = () => {
    setName("");
    setDescription("");
    setFields([{ name: "", label: "", field_type: "text", required: false, options: [] }]);
  };

  const addField = () => {
    setFields([...fields, { name: "", label: "", field_type: "text", required: false, options: [] }]);
  };

  const removeField = (idx) => {
    setFields(fields.filter((_, i) => i !== idx));
  };

  const updateField = (idx, key, value) => {
    const updated = [...fields];
    updated[idx] = { ...updated[idx], [key]: value };
    setFields(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearMsg();
    const validFields = fields.filter((f) => f.name && f.label);
    if (validFields.length === 0) {
      setError("Agrega al menos un campo a la plantilla.");
      return;
    }
    try {
      const payload = {
        name,
        description: description || null,
        fields: validFields.map((f) => ({
          name: f.name,
          label: f.label,
          field_type: f.field_type,
          required: f.required,
          options: f.options?.length ? f.options : null,
        })),
      };
      if (editingTemplate) {
        await updateTemplate(editingTemplate.id, payload);
        setSuccess("Plantilla actualizada.");
      } else {
        await createTemplate(payload);
        setSuccess("Plantilla creada.");
      }
      setShowCreate(false);
      setEditingTemplate(null);
      resetForm();
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error al guardar plantilla");
    }
  };

  const handleToggleStatus = async (template) => {
    clearMsg();
    try {
      await updateTemplateStatus(template.id, !template.is_active);
      setSuccess(`Plantilla ${template.is_active ? "desactivada" : "activada"}.`);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Error");
    }
  };

  const startEdit = (template) => {
    setEditingTemplate(template);
    setShowCreate(true);
    setName(template.name);
    setDescription(template.description || "");
    try {
      const parsed = JSON.parse(template.fields_json);
      setFields(parsed.map((f) => ({
        name: f.name || "",
        label: f.label || "",
        field_type: f.field_type || "text",
        required: f.required || false,
        options: f.options || [],
      })));
    } catch {
      setFields([{ name: "", label: "", field_type: "text", required: false, options: [] }]);
    }
  };

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Plantillas de captura</h1>
          <p className="page-subtitle">Define la estructura de los formularios de registro.</p>
        </div>
        <button className="button button-primary" onClick={() => { setShowCreate(!showCreate); setEditingTemplate(null); resetForm(); }}>
          {showCreate ? "Cancelar" : "+ Nueva plantilla"}
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {showCreate && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="section-title">{editingTemplate ? "Editar plantilla" : "Nueva plantilla"}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre de la plantilla *</label>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Descripción</label>
                <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
            </div>

            <h4 style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 16, marginBottom: 10 }}>Campos del formulario</h4>

            {fields.map((field, idx) => (
              <div key={idx} className="card" style={{ marginBottom: 10, padding: 12, background: "var(--bg-primary)" }}>
                <div className="form-row">
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Identificador</label>
                    <input className="input" placeholder="nombre_campo" value={field.name} onChange={(e) => updateField(idx, "name", e.target.value)} />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Etiqueta visible</label>
                    <input className="input" placeholder="Nombre visible" value={field.label} onChange={(e) => updateField(idx, "label", e.target.value)} />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Tipo</label>
                    <select className="select" value={field.field_type} onChange={(e) => updateField(idx, "field_type", e.target.value)}>
                      {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
                    <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4, color: "var(--text-muted)" }}>
                      <input type="checkbox" checked={field.required} onChange={(e) => updateField(idx, "required", e.target.checked)} />
                      Requerido
                    </label>
                    {fields.length > 1 && (
                      <button type="button" className="button button-danger button-sm" onClick={() => removeField(idx)}>×</button>
                    )}
                  </div>
                </div>
                {(field.field_type === "select" || field.field_type === "multiselect") && (
                  <div className="form-group" style={{ marginTop: 8, marginBottom: 0 }}>
                    <label>Opciones (separadas por coma)</label>
                    <input
                      className="input"
                      placeholder="opción1, opción2, opción3"
                      value={(field.options || []).join(", ")}
                      onChange={(e) => updateField(idx, "options", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
                    />
                  </div>
                )}
              </div>
            ))}

            <div className="toolbar" style={{ marginTop: 8 }}>
              <button type="button" className="button button-ghost" onClick={addField}>+ Agregar campo</button>
              <button type="submit" className="button button-primary">{editingTemplate ? "Guardar cambios" : "Crear plantilla"}</button>
              {editingTemplate && (
                <button type="button" className="button button-secondary" onClick={() => { setEditingTemplate(null); setShowCreate(false); resetForm(); }}>Cancelar</button>
              )}
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <h3 className="section-title">Plantillas registradas</h3>
        {loading ? <p className="loading">Cargando...</p> : templates.length === 0 ? (
          <div className="empty-state"><p>No hay plantillas creadas.</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Descripción</th>
                  <th>Campos</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => {
                  let fieldCount = 0;
                  try { fieldCount = JSON.parse(t.fields_json).length; } catch { /* ignore */ }
                  return (
                    <tr key={t.id}>
                      <td style={{ fontWeight: 500 }}>{t.name}</td>
                      <td style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis" }}>{t.description || "–"}</td>
                      <td>
                        <span className="badge badge-valid">{fieldCount} campos</span>
                      </td>
                      <td>
                        <span className={`badge ${t.is_active ? "badge-active" : "badge-inactive"}`}>
                          {t.is_active ? "Activa" : "Inactiva"}
                        </span>
                      </td>
                      <td>
                        <div className="toolbar">
                          <button className="button button-ghost button-sm" onClick={() => startEdit(t)}>Editar</button>
                          <button
                            className={`button button-sm ${t.is_active ? "button-warning" : "button-success"}`}
                            onClick={() => handleToggleStatus(t)}
                          >
                            {t.is_active ? "Desactivar" : "Activar"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

export default TemplatesPage;
