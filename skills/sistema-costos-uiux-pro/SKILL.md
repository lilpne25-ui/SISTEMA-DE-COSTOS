---
name: sistema-costos-uiux-pro
description: Mejorar y redisenar la experiencia UI/UX del Sistema de Costos en PySide6 con un nivel profesional, consistente y mantenible. Usar cuando se trabajen ventanas, formularios, tablas, flujos de captura, navegacion, estados vacios/error/carga, jerarquia visual, accesibilidad, feedback al usuario o estandarizacion visual de todo el sistema.
---

# Sistema Costos UIUX Pro

## Objetivo

Elevar la interfaz completa del sistema a un estandar profesional sin romper la logica de negocio ni la arquitectura existente.

## Flujo de trabajo

1. Auditar la pantalla objetivo: tareas frecuentes, fricciones, pasos innecesarios y claridad de labels.
2. Priorizar cambios de alto impacto: legibilidad, menos clics, mejor orden de captura y errores accionables.
3. Definir estructura visual: cabecera de contexto, filtros, tabla principal, panel de detalle y acciones.
4. Implementar cambios pequenos por modulo con refactor seguro.
5. Validar con pruebas funcionales y recorrido manual de usuario.

## Reglas de diseno visual

- Mantener estilo sobrio y profesional (desktop industrial), sin efectos decorativos innecesarios.
- Usar consistencia de espaciado (4/8/12/16/24) y alturas uniformes para controles.
- Mantener jerarquia tipografica clara:
  - Titulos de seccion visibles.
  - Labels cortos y precisos.
  - Texto de ayuda solo cuando agrega contexto real.
- Estandarizar botones por jerarquia:
  - Primario: accion principal del flujo.
  - Secundario: acciones de apoyo.
  - Peligro: eliminar/destructivo con confirmacion.
- Homologar tablas:
  - Encabezados claros.
  - Orden visual estable.
  - Seleccion de fila evidente.
  - Columnas con datos criticos primero.

## Reglas de UX

- Reducir carga cognitiva: pedir solo los datos necesarios para la tarea actual.
- Mostrar estado de sistema siempre: listo, guardando, error, sin datos.
- Prevenir errores antes de guardar: validacion temprana y mensajes accionables.
- Evitar bloqueos silenciosos: toda falla debe informar causa y siguiente paso.
- Confirmar acciones destructivas y exigir contrasena cuando aplique.
- Mantener recorridos cortos:
  - Buscar
  - Seleccionar
  - Editar/Agregar
  - Confirmar

## Formularios profesionales

- Ordenar campos por frecuencia de uso.
- Definir defaults utiles.
- Evitar campos editables cuando deben ser controlados por catalogo.
- Mostrar unidad y moneda en contexto del campo.
- Usar placeholders solo como ayuda, no como reemplazo de label.
- Marcar obligatorios de forma consistente.

## Tablas y filtros

- El combo de filtros debe ser dinamico desde BD, nunca hardcodeado.
- "Todos" como opcion base y luego catalogos reales.
- Evitar duplicados visuales entre catalogo y datos historicos.
- Mantener busqueda por columnas relevantes del flujo.

## Arquitectura y mantenimiento

- Mantener separacion `ui/`, `data/`, `models/`, `services/`.
- No mover reglas de negocio al widget si pueden ir al repositorio/servicio.
- Reusar componentes de UI cuando un patron se repite.
- Encapsular cambios de persistencia en `Repository`.

## Checklist de terminado

- La pantalla es mas clara que antes.
- El flujo principal se ejecuta con menos pasos o menos errores.
- No hay hardcodes de catalogos o filtros.
- Todos los mensajes al usuario son claros y accionables.
- El cambio compila y mantiene comportamiento esperado.
- La implementacion es facil de mantener para futuras mejoras.

## Respuesta al usuario

- Resumir en pocas lineas: que mejoro, donde y como se valida.
- Priorizar impacto visual y de flujo, no listar detalles menores.
