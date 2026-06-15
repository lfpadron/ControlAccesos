# Access Manager Print Agent

El Print Agent será un componente local, instalado cerca de las impresoras del complejo médico. Su responsabilidad futura será recibir trabajos autorizados desde la plataforma y convertirlos en comandos de impresión para impresoras térmicas, láser o equipos definidos por cada torre.

En este primer entregable solo se deja la estructura base:

- `agent.py`: proceso placeholder con log de arranque.
- `Containerfile`: imagen mínima Python.

No se implementa impresión real todavía. La integración futura debe contemplar autenticación del agente, cola de trabajos, cifrado de configuración local y auditoría por cada impresión.
