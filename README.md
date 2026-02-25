# Descarga automática del Estado Diario de Marcas (INAPI)

Este proyecto descarga automáticamente el PDF más reciente publicado en:

- https://tramites.inapi.cl/EstadosDiariosMarcas

## ¿Qué hace el script?

El script `scripts/descargar_estado_diario.py`:

1. Obtiene el HTML de la página de Estado Diario de Marcas.
2. Detecta todos los enlaces a archivos PDF.
3. Identifica el archivo más reciente (por fecha encontrada en la URL y, si no existe, por `Last-Modified`).
4. Descarga el PDF y lo guarda en `downloads/` con formato:
   - `INAPI_EstadoDiario_Marcas_YYYY-MM-DD.pdf`
5. Registra el resultado en `logs/descarga.log` indicando fecha/hora y estado (`OK` o `ERROR`).

## Estructura esperada

- `scripts/descargar_estado_diario.py`: script principal.
- `downloads/`: carpeta destino de los PDF descargados.
- `logs/descarga.log`: historial de ejecuciones.
- `.github/workflows/descarga-estado-diario.yml`: ejecución automática diaria.

## Ejecución local

Desde la raíz del repositorio:

```bash
python scripts/descargar_estado_diario.py
```

## Ejecución automática con GitHub Actions

El workflow se encuentra en:

- `.github/workflows/descarga-estado-diario.yml`

Está configurado para correr diariamente y considerar el cambio horario de Chile:

- `0 12 * * *`
- `0 13 * * *`

Como GitHub Actions usa UTC, se ejecutan ambos horarios y luego una validación interna (`TZ=America/Santiago`) asegura que la descarga solo ocurra exactamente a las `09:00` hora de Chile.

## ¿Cómo cambiar la hora de ejecución?

1. Abre `.github/workflows/descarga-estado-diario.yml`.
2. Edita los cron en UTC dentro de `on.schedule`.
3. Ajusta también la validación en el paso `Validar hora local de Chile`:

```bash
if [ "$HORA_CHILE" != "09:00" ]; then
```

Por ejemplo, para ejecutar a las 10:30 hora de Chile, cambia esa validación a `10:30` y actualiza los cron UTC correspondientes para horario de verano/invierno.
