/* ============================================================
   Inicio de sesion (RF4)
   ============================================================ */

const formulario = document.getElementById("formLogin");
const mensajeError = document.getElementById("mensajeError");
const btnIngresar = document.getElementById("btnIngresar");

// Si ya hay una sesion activa, se entra directo al panel
if (API.obtenerToken()) {
  window.location.replace("dashboard.html");
}

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensajeError.textContent = "";

  const correo = document.getElementById("correo").value.trim();
  const contrasena = document.getElementById("contrasena").value;

  if (!correo || !contrasena) {
    mensajeError.textContent = "Debe ingresar su correo y contraseña.";
    return;
  }

  btnIngresar.disabled = true;
  btnIngresar.textContent = "Verificando…";

  try {
    const datos = await API.login(correo, contrasena);
    API.guardarSesion(datos.token, datos.usuario);
    window.location.href = "dashboard.html";
  } catch (error) {
    mensajeError.textContent =
      error.message === "Failed to fetch"
        ? "No se pudo contactar al servidor. Verifique que el backend esté en ejecución."
        : error.message;
    btnIngresar.disabled = false;
    btnIngresar.textContent = "Iniciar sesión";
  }
});
