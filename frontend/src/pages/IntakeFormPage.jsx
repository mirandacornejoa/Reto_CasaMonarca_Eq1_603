import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import { useAuth } from "../hooks/useAuth";
import { createRecord } from "../api/recordsApi";
import { COUNTRIES } from "../data/countries";
import {
  GENDER_OPTIONS,
  CIVIL_STATUS_OPTIONS,
  AGE_RANGE_OPTIONS,
  POPULATION_GROUPS,
} from "../constants";

function IntakeFormPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const level = user?.access_level_code;
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);

  const [form, setForm] = useState({
    first_name: "",
    last_name_1: "",
    last_name_2: "X",
    phone: "",
    gender: "",
    country_of_origin: "",
    state_department: "",
    civil_status: "",
    birth_date: "",
    age_range: "",
    population_group: "",
    observations: "",
  });

  const set = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.first_name.trim() || !form.last_name_1.trim()) {
      setError("Nombre de pila y primer apellido son obligatorios.");
      return;
    }
    if (!privacyAccepted) {
      setError("Debe aceptar el aviso de privacidad para continuar.");
      return;
    }
    if (!termsAccepted) {
      setError("Debe aceptar los términos y condiciones para continuar.");
      return;
    }

    setSubmitting(true);
    try {
      const submitDate = new Date().toISOString().split("T")[0];
      await createRecord({
        attention_date: submitDate,
        first_name: form.first_name.trim(),
        last_name_1: form.last_name_1.trim(),
        last_name_2: form.last_name_2.trim() || "X",
        phone: form.phone.trim() || null,
        gender: form.gender || null,
        country_of_origin: form.country_of_origin || null,
        state_department: form.state_department.trim() || null,
        civil_status: form.civil_status || null,
        birth_date: form.birth_date || null,
        age_range: form.age_range || null,
        population_group: form.population_group || null,
        observations: form.observations.trim() || null,
      });
      setSuccess("✓ Beneficiario registrado correctamente.");
      // Nivel 4 (voluntario) no puede ver registros: reiniciar formulario
      if (level >= 4) {
        setTimeout(() => {
          setSuccess("");
          setPrivacyAccepted(false);
          setTermsAccepted(false);
          setForm({
            first_name: "", last_name_1: "", last_name_2: "X",
            phone: "", gender: "", country_of_origin: "", state_department: "",
            civil_status: "", birth_date: "", age_range: "", population_group: "", observations: "",
          });
        }, 2000);
      } else {
        setTimeout(() => navigate("/records"), 2000);
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Error al registrar beneficiario"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="container">
      <AppNav />

      <div className="header">
        <div>
          <h1 className="page-title">Entrevista de ingreso al albergue</h1>
          <p className="page-subtitle">
            Casa Monarca · Ayuda Humanitaria al Migrante, A.B.P.
          </p>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card intake-form">
        <form onSubmit={handleSubmit}>
          {/* Fecha de atención: se registra automáticamente al enviar */}

          {/* ── Sección 2: Datos personales ── */}
          <div className="form-section">
            <div className="section-header">👤 Datos personales</div>
            <div className="form-row">
              <div className="form-group">
                <label>Nombre de pila (sin apellidos) *</label>
                <input
                  className="input"
                  value={form.first_name}
                  onChange={set("first_name")}
                  placeholder="Ej. María"
                  required
                />
              </div>
              <div className="form-group">
                <label>Primer apellido *</label>
                <input
                  className="input"
                  value={form.last_name_1}
                  onChange={set("last_name_1")}
                  placeholder="Ej. García"
                  required
                />
              </div>
              <div className="form-group">
                <label>Segundo apellido</label>
                <input
                  className="input"
                  value={form.last_name_2}
                  onChange={set("last_name_2")}
                  placeholder="X"
                />
                <span className="field-note">
                  Si no tiene, poner X
                </span>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Número telefónico de contacto</label>
                <input
                  className="input"
                  value={form.phone}
                  onChange={set("phone")}
                  placeholder="+52 81 1234 5678"
                />
              </div>
              <div className="form-group">
                <label>Género</label>
                <select
                  className="select"
                  value={form.gender}
                  onChange={set("gender")}
                >
                  <option value="">-- Seleccionar --</option>
                  {GENDER_OPTIONS.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* ── Sección 3: Origen ── */}
          <div className="form-section">
            <div className="section-header">🌍 Origen</div>
            <div className="form-row">
              <div className="form-group">
                <label>País de origen</label>
                <select
                  className="select"
                  value={form.country_of_origin}
                  onChange={set("country_of_origin")}
                >
                  <option value="">-- Seleccionar --</option>
                  {COUNTRIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Departamento / Estado</label>
                <input
                  className="input"
                  value={form.state_department}
                  onChange={set("state_department")}
                  placeholder="Ej. Tegucigalpa"
                />
              </div>
            </div>
          </div>

          {/* ── Sección 4: Datos demográficos ── */}
          <div className="form-section">
            <div className="section-header">📊 Datos demográficos</div>
            <div className="form-row">
              <div className="form-group">
                <label>Estado civil</label>
                <select
                  className="select"
                  value={form.civil_status}
                  onChange={set("civil_status")}
                >
                  <option value="">-- Seleccionar --</option>
                  {CIVIL_STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Fecha de nacimiento</label>
                <input
                  className="input"
                  type="date"
                  value={form.birth_date}
                  onChange={set("birth_date")}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Edad</label>
                <select
                  className="select"
                  value={form.age_range}
                  onChange={set("age_range")}
                >
                  <option value="">-- Seleccionar --</option>
                  {AGE_RANGE_OPTIONS.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Grupo de población</label>
                <select
                  className="select"
                  value={form.population_group}
                  onChange={set("population_group")}
                >
                  <option value="">-- Seleccionar --</option>
                  {POPULATION_GROUPS.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* ── Sección 5: Observaciones ── */}
          <div className="form-section">
            <div className="section-header">📝 Observaciones</div>
            <div className="form-group">
              <label>Observaciones adicionales</label>
              <textarea
                className="input"
                rows={4}
                value={form.observations}
                onChange={set("observations")}
                placeholder="Notas adicionales sobre el beneficiario..."
                style={{ resize: "vertical" }}
              />
            </div>
          </div>

          {/* ── Aviso de privacidad + Términos y condiciones ── */}
          <div className="form-section" style={{ background: "var(--bg-secondary)", borderRadius: 8, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 14 }}>
              <input
                type="checkbox"
                checked={privacyAccepted}
                onChange={(e) => setPrivacyAccepted(e.target.checked)}
                style={{ marginTop: 2, accentColor: "var(--accent)", width: 16, height: 16, flexShrink: 0 }}
              />
              <span>
                He leído y acepto el{" "}
                <button
                  type="button"
                  style={{ color: "var(--accent)", textDecoration: "underline", background: "none", border: "none", cursor: "pointer", padding: 0, fontSize: "inherit" }}
                  onClick={() => setShowPrivacyModal(true)}
                >
                  Aviso de Privacidad
                </button>
                {" "}de Casa Monarca, A.B.P. El beneficiario ha sido informado sobre el tratamiento de sus datos personales.
              </span>
            </label>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 14 }}>
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                style={{ marginTop: 2, accentColor: "var(--accent)", width: 16, height: 16, flexShrink: 0 }}
              />
              <span>
                He leído y acepto los{" "}
                <button
                  type="button"
                  style={{ color: "var(--accent)", textDecoration: "underline", background: "none", border: "none", cursor: "pointer", padding: 0, fontSize: "inherit" }}
                  onClick={() => setShowTermsModal(true)}
                >
                  Términos y Condiciones
                </button>
                {" "}de uso del sistema de gestión de información de Casa Monarca, A.B.P.
              </span>
            </label>
          </div>

          <div className="toolbar" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="button button-ghost"
              onClick={() => navigate("/records")}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="button button-primary"
              disabled={submitting || !privacyAccepted || !termsAccepted}
            >
              {submitting ? "Registrando..." : "Registrar beneficiario"}
            </button>
          </div>
        </form>
      </div>

      {/* ── Modal Aviso de Privacidad ── */}
      {showPrivacyModal && (
        <div className="modal-overlay" onClick={() => setShowPrivacyModal(false)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640, maxHeight: "80vh", overflowY: "auto" }}>
            <h3 className="section-title">Aviso de Privacidad</h3>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
              Casa Monarca · Ayuda Humanitaria al Migrante, A.B.P.
            </p>
            <div style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text-secondary)" }}>
              <p><strong>Responsable del tratamiento:</strong> Casa Monarca, Ayuda Humanitaria al Migrante, A.B.P., con domicilio en Monterrey, Nuevo León, México.</p>
              <p><strong>Finalidad del tratamiento:</strong> Los datos personales recabados serán utilizados exclusivamente para brindar atención humanitaria, seguimiento de casos, elaboración de estadísticas internas y cumplimiento de obligaciones legales propias de la actividad de la asociación.</p>
              <p><strong>Datos recabados:</strong> Nombre, apellidos, fecha de nacimiento, género, nacionalidad, país de origen, estado civil, datos de contacto, grupo de población y cualquier otra información proporcionada voluntariamente durante la entrevista de ingreso.</p>
              <p><strong>Transferencia de datos:</strong> Los datos no serán transferidos a terceros sin consentimiento expreso del titular, salvo las excepciones previstas en la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP).</p>
              <p><strong>Derechos ARCO:</strong> El titular tiene derecho a Acceder, Rectificar, Cancelar u Oponerse al tratamiento de sus datos personales. Para ejercer estos derechos puede presentar una solicitud directamente con el personal de Casa Monarca o a través del sistema de gestión.</p>
              <p><strong>Consentimiento:</strong> El personal que registra estos datos certifica que el beneficiario fue informado sobre este aviso de privacidad y otorgó su consentimiento expreso para el tratamiento de sus datos.</p>
              <p style={{ color: "var(--text-muted)", marginTop: 12 }}>Última actualización: 2026. Este aviso puede modificarse; cualquier cambio será comunicado a través de los canales internos de la asociación.</p>
            </div>
            <div className="toolbar" style={{ marginTop: 16 }}>
              <button className="button button-ghost" onClick={() => setShowPrivacyModal(false)}>
                Cerrar
              </button>
              <button className="button button-primary" onClick={() => { setPrivacyAccepted(true); setShowPrivacyModal(false); }}>
                He leído y acepto
              </button>
            </div>
          </div>
        </div>
      )}
      {/* ── Modal Términos y Condiciones ── */}
      {showTermsModal && (
        <div className="modal-overlay" onClick={() => setShowTermsModal(false)}>
          <div className="card modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640, maxHeight: "80vh", overflowY: "auto" }}>
            <h3 className="section-title">Términos y Condiciones de Uso</h3>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
              Sistema de Gestión de Información — Casa Monarca, A.B.P.
            </p>
            <div style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text-secondary)" }}>
              <p><strong>1. Uso autorizado del sistema:</strong> El acceso y uso del sistema de gestión de información de Casa Monarca es exclusivo para el personal autorizado de la asociación. Queda prohibido el uso del sistema para fines distintos a la atención humanitaria y operación interna de la asociación.</p>
              <p><strong>2. Confidencialidad de la información:</strong> Toda la información registrada en el sistema es estrictamente confidencial. El personal autorizado se compromete a no divulgar, compartir ni utilizar los datos de los beneficiarios fuera del contexto operativo de Casa Monarca, salvo autorización expresa de la coordinación.</p>
              <p><strong>3. Responsabilidad del usuario:</strong> Cada usuario es responsable de las acciones realizadas con sus credenciales de acceso. Está prohibido compartir contraseñas o accesos con terceros. El uso indebido del sistema puede resultar en la revocación del acceso y consecuencias disciplinarias o legales.</p>
              <p><strong>4. Integridad de los datos:</strong> El personal se compromete a registrar información veraz, completa y actualizada. La alteración, eliminación o manipulación no autorizada de registros está estrictamente prohibida y será registrada en la bitácora del sistema.</p>
              <p><strong>5. Seguridad y certificados:</strong> Los certificados de firma digital emitidos por el sistema son de uso personal e intransferible. El usuario es responsable de la custodia de su archivo de clave privada (.key) y de su contraseña de firma.</p>
              <p><strong>6. Derechos ARCO:</strong> Al registrar información de un beneficiario, el personal certifica que el titular fue informado de sus derechos de Acceso, Rectificación, Cancelación y Oposición (ARCO) conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares.</p>
              <p><strong>7. Auditoría:</strong> Todas las operaciones realizadas en el sistema quedan registradas en la bitácora de auditoría de forma inmutable. El personal acepta que sus acciones pueden ser revisadas por la administración de Casa Monarca.</p>
              <p style={{ color: "var(--text-muted)", marginTop: 12 }}>Versión 1.0 — 2026. Casa Monarca, Ayuda Humanitaria al Migrante, A.B.P.</p>
            </div>
            <div className="toolbar" style={{ marginTop: 16 }}>
              <button className="button button-ghost" onClick={() => setShowTermsModal(false)}>
                Cerrar
              </button>
              <button className="button button-primary" onClick={() => { setTermsAccepted(true); setShowTermsModal(false); }}>
                He leído y acepto
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default IntakeFormPage;
