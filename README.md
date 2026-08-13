# Generador de Renta Persona Natural — Colombia AG 2025

Herramienta local (privada, sin envío de datos a internet) para preparar la
declaración de renta de una persona natural residente fiscal, Año Gravable
2025, y guiar el diligenciamiento del Formulario 210 en la DIAN.

## ⚠️ Alcance y advertencias importantes

- Válida **exclusivamente para el AG2025** (declaración presentada en 2026)
  y para personas naturales **residentes fiscales** que declaran en el
  Formulario 210.
- La información exógena **no es la declaración**. La herramienta nunca
  convierte automáticamente un valor reportado por terceros en ingreso
  gravable: todo pasa por el módulo de **Ingresos/Conciliación**, donde
  usted confirma su tratamiento real.
- Los números de casilla del módulo **Formulario 210** corresponden a la
  estructura pública documentada de dicho formulario (Resolución DIAN
  000044 de 2024, vigente para AG2025). **Verifique cada casilla contra el
  formulario oficial en MUISCA** antes de presentar.
- Ningún beneficio tributario se aplica automáticamente al cálculo: usted
  debe marcar expresamente que cuenta con el soporte documental exigido.
- Esta herramienta es un apoyo de preparación. No reemplaza el criterio
  profesional de un contador o asesor tributario, especialmente en casos
  complejos (no residentes, régimen simple, sucesiones, etc.).

## Requisitos

- Python 3.10 o superior (probado con 3.14).
- Paquetes: `streamlit`, `openpyxl`, `pandas` (ver `requirements.txt`).

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

Desde la carpeta `renta-ag2025`:

```bash
streamlit run app.py
```

Se abrirá en `http://localhost:8501`. Todo el procesamiento ocurre en su
computador; los datos se guardan en `data/renta.db` (SQLite local) y los
archivos Excel cargados en `data/uploads/`. Nada se envía a servicios
externos.

## Flujo de uso

1. **Contribuyente** — cree el perfil del declarante (identificación,
   residencia fiscal, dependientes, etc.). Esto activa una "declaración".
2. **Exógena** — cargue el archivo `.xlsx` de "Consulta de información
   reportada por terceros" descargado de la DIAN. Se clasifica
   automáticamente con reglas, sin asumir que todo es ingreso.
3. **Ingresos** — revise y confirme/edite el estado de cada registro;
   luego indique los valores definitivos por cédula (trabajo, capital, no
   laboral, pensiones, dividendos) que alimentan el motor de liquidación.
4. **Patrimonio** — registre activos y pasivos a 31/12/2025.
5. **Deducciones** — indique valores de posibles beneficios (dependientes,
   intereses de vivienda, medicina prepagada, GMF, AFC/pensiones
   voluntarias, facturación electrónica) y marque si cuenta con el soporte.
6. **Optimización** — compare escenarios (sin beneficios / con beneficios
   soportados / hipotético con todos los detectados) para ver el ahorro
   legal disponible.
7. **Liquidación** — vea el cálculo completo y trazable del impuesto.
8. **Formulario 210** — vea el resultado casilla por casilla, con origen,
   explicación y soporte requerido de cada una.
9. **Auditoría** — revise alertas de inconsistencias antes de presentar.
10. **Informe final** — checklist de verificación y descarga del informe
    ejecutivo (.txt).

## Nueva declaración / múltiples contribuyentes

Use el botón **"➕ Nueva declaración"** en la barra lateral para preparar
la declaración de otro contribuyente sin perder las anteriores ni tocar el
código. Cada declaración se identifica por tipo de documento +
identificación + año gravable, y puede eliminarse de forma segura desde
el menú "Zona de riesgo" en la barra lateral.

## Parámetros tributarios usados (AG2025)

Ver `core/config.py` — cada valor incluye su fuente normativa (UVT 2025 =
$49.799, tabla del Art. 241 ET, límites de deducciones del Art. 336 ET,
etc.). No modifique estos valores sin verificar la norma correspondiente.

## Estructura del proyecto

```
renta-ag2025/
  app.py                  # Página de Inicio (dashboard)
  pages/                  # Módulos 2-11 del menú (Streamlit multipágina)
  core/
    config.py             # Parámetros tributarios AG2025 (única fuente de verdad)
    db.py                 # Persistencia local SQLite
    importer.py           # Parser del Excel de exógena DIAN
    conciliacion.py        # Motor de clasificación de conceptos
    patrimonio.py          # Cálculo de patrimonio
    deducciones.py         # Motor de beneficios tributarios
    liquidacion.py         # Motor de liquidación del impuesto
    optimizador.py         # Comparación de escenarios
    formulario210.py       # Mapeo a casillas del Formulario 210
    auditoria.py           # Control de diferencias
    informe.py              # Checklist e informe ejecutivo
    ui_common.py            # Utilidades compartidas de la interfaz
  data/                    # Base de datos local y archivos cargados (NO subir a la nube)
```
