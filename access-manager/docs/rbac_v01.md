# RBAC v01

RBAC queda implementado como estructura inicial y dependencia de autorización. Todavía no es una matriz granular completa por permiso.

## Roles Semilla

- `ADMIN_SISTEMA`: administración global.
- `ADMIN_NEGOCIO`: administración por institución o complejo.
- `RECEPCIONISTA`: recepción operativa.
- `MEDICO`: acceso futuro del médico.
- `OPERADOR`: apoyo operativo.
- `GUARDIA_CONTINGENCIA`: rol limitado para contingencias.
- `USUARIO_KIOSKO`: rol técnico para kioskos.

## Reglas Actuales

- Los endpoints operativos requieren `ADMIN_SISTEMA` o `ADMIN_NEGOCIO`.
- Los endpoints de turnos llamados aceptan roles operativos: `RECEPCIONISTA`, `MEDICO` y `OPERADOR`, además de administradores.
- El endpoint público de display autentica por código de dispositivo y token si la pantalla lo tiene configurado.
- `ADMIN_SISTEMA` puede operar globalmente.
- Las asignaciones de `usuario_roles` ya permiten guardar alcance por institución y complejo.
- La validación fina del alcance institucional queda marcada como pendiente.

## Pendientes

- Matriz explícita de permisos por endpoint y acción.
- Validación de alcance para `ADMIN_NEGOCIO` por institución/complejo.
- Roles de solo lectura.
- Auditoría de login y denegaciones de acceso.
- Pruebas específicas para permisos negativos y alcance cruzado.
