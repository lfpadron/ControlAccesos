--
-- PostgreSQL database dump
--

\restrict xiSg355ILmL7XnppJQdKwV4BKRrtgvB0bsdnONUUXmgHHiQD7pXrwDD3kDvG8EK

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO access_manager;

--
-- Name: asignaciones_medico_consultorio; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.asignaciones_medico_consultorio (
    id uuid NOT NULL,
    medico_id uuid NOT NULL,
    consultorio_id uuid NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date,
    hora_inicio time without time zone,
    hora_fin time without time zone,
    dias_semana character varying(120),
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.asignaciones_medico_consultorio OWNER TO access_manager;

--
-- Name: asignaciones_operador; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.asignaciones_operador (
    id uuid NOT NULL,
    operador_id uuid NOT NULL,
    medico_id uuid,
    consultorio_id uuid,
    complejo_id uuid NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date,
    prioridad integer DEFAULT 100 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_asignaciones_operador_ck_asignaciones_operador_destino CHECK (((medico_id IS NOT NULL) OR (consultorio_id IS NOT NULL)))
);


ALTER TABLE public.asignaciones_operador OWNER TO access_manager;

--
-- Name: auditoria; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.auditoria (
    id uuid NOT NULL,
    evento character varying(120) NOT NULL,
    entidad character varying(120) NOT NULL,
    entidad_id uuid,
    usuario_id uuid,
    canal character varying(64),
    ip_origen character varying(64),
    valor_antes jsonb,
    valor_despues jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.auditoria OWNER TO access_manager;

--
-- Name: citas; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.citas (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    cluster_espera_id uuid,
    consultorio_id uuid NOT NULL,
    estado character varying(40) DEFAULT 'AGENDADA'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tipo character varying(24) NOT NULL,
    paciente_id uuid NOT NULL,
    medico_id uuid NOT NULL,
    sala_prevista_id uuid,
    fecha_cita date NOT NULL,
    hora_cita time without time zone NOT NULL,
    duracion_estimada integer,
    folio_turno character varying(4) NOT NULL,
    origen character varying(80),
    notas_operativas text,
    creada_por uuid,
    CONSTRAINT ck_citas_ck_citas_estado_valido CHECK (((estado)::text = ANY ((ARRAY['AGENDADA'::character varying, 'QR_GENERADO'::character varying, 'LLEGO_LOBBY'::character varying, 'AUTORIZADO_PASAR'::character varying, 'EN_CONSULTA'::character varying, 'FINALIZADA'::character varying, 'NO_LLEGO'::character varying, 'CANCELADA'::character varying, 'EXPIRADA'::character varying])::text[]))),
    CONSTRAINT ck_citas_ck_citas_tipo_valido CHECK (((tipo)::text = ANY ((ARRAY['PROGRAMADA'::character varying, 'ESPONTANEA'::character varying])::text[])))
);


ALTER TABLE public.citas OWNER TO access_manager;

--
-- Name: clusters_turnos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.clusters_turnos (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.clusters_turnos OWNER TO access_manager;

--
-- Name: complejos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.complejos (
    id uuid NOT NULL,
    institucion_id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    descripcion text,
    logo_url character varying(500),
    direccion text,
    telefono character varying(64),
    zona_horaria character varying(64) NOT NULL,
    color_primario character varying(32),
    color_secundario character varying(32),
    color_acento character varying(32),
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.complejos OWNER TO access_manager;

--
-- Name: consultorios; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.consultorios (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    codigo character varying(80) NOT NULL,
    nombre_visible character varying(180),
    instrucciones_acceso text,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.consultorios OWNER TO access_manager;

--
-- Name: consultorios_clusters; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.consultorios_clusters (
    consultorio_id uuid NOT NULL,
    cluster_id uuid NOT NULL
);


ALTER TABLE public.consultorios_clusters OWNER TO access_manager;

--
-- Name: contactos_institucionales; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.contactos_institucionales (
    id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    medios_contacto jsonb NOT NULL,
    tipo_contacto character varying(32) NOT NULL,
    notas text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tipo_contacto_descripcion character varying(50),
    CONSTRAINT ck_contactos_institucionales_ck_contactos_institucional_8d7e CHECK (((tipo_contacto)::text = ANY ((ARRAY['PRIMARIO'::character varying, 'SECUNDARIO'::character varying, 'SOLO_EMERGENCIAS'::character varying, 'OTRO'::character varying])::text[])))
);


ALTER TABLE public.contactos_institucionales OWNER TO access_manager;

--
-- Name: contactos_institucionales_complejos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.contactos_institucionales_complejos (
    contacto_id uuid NOT NULL,
    complejo_id uuid NOT NULL
);


ALTER TABLE public.contactos_institucionales_complejos OWNER TO access_manager;

--
-- Name: eventos_llegada; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.eventos_llegada (
    id uuid NOT NULL,
    cita_id uuid NOT NULL,
    tipo character varying(32) NOT NULL,
    sala_id uuid,
    canal character varying(32) NOT NULL,
    usuario_id uuid,
    dispositivo_id character varying(120),
    ip_origen character varying(80),
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_eventos_llegada_ck_eventos_llegada_canal_valido CHECK (((canal)::text = ANY ((ARRAY['KIOSKO'::character varying, 'RECEPCION'::character varying, 'OPERADOR'::character varying, 'APP_MOVIL'::character varying, 'BOT_TELEGRAM'::character varying, 'API_EXTERNA'::character varying])::text[]))),
    CONSTRAINT ck_eventos_llegada_ck_eventos_llegada_tipo_valido CHECK (((tipo)::text = ANY ((ARRAY['CHECKIN_LOBBY'::character varying, 'CHECKIN_SALA'::character varying])::text[])))
);


ALTER TABLE public.eventos_llegada OWNER TO access_manager;

--
-- Name: instituciones; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.instituciones (
    id uuid NOT NULL,
    nombre character varying(120) NOT NULL,
    razon_social character varying(120),
    logo_url character varying(500),
    color_primario character varying(32),
    color_secundario character varying(32),
    color_acento character varying(32),
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    notas character varying(500)
);


ALTER TABLE public.instituciones OWNER TO access_manager;

--
-- Name: kioskos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.kioskos (
    id uuid NOT NULL,
    codigo_dispositivo character varying(120) NOT NULL,
    token_hash character varying(255) NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    punto_acceso_id uuid NOT NULL,
    nombre character varying(180),
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    ultima_conexion timestamp with time zone,
    polling_interval_seconds integer DEFAULT 5 NOT NULL,
    color_fondo character varying(40),
    color_texto character varying(40),
    color_primario character varying(40),
    color_acento character varying(40),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_kioskos_kioskos_polling_interval_range CHECK (((polling_interval_seconds >= 2) AND (polling_interval_seconds <= 30)))
);


ALTER TABLE public.kioskos OWNER TO access_manager;

--
-- Name: medicos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.medicos (
    id uuid NOT NULL,
    usuario_id uuid,
    nombre character varying(180) NOT NULL,
    apellidos character varying(180) NOT NULL,
    nombre_visible character varying(220),
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    plantilla_turno character varying(40) DEFAULT 'PACIENTE_CONSULTORIO'::character varying NOT NULL,
    CONSTRAINT ck_medicos_ck_medicos_plantilla_turno CHECK (((plantilla_turno)::text = ANY ((ARRAY['PACIENTE_CONSULTORIO'::character varying, 'TURNO_PACIENTE_CONSULTORIO'::character varying, 'PACIENTE_TURNO_CONSULTORIO'::character varying, 'TURNO_CONSULTORIO'::character varying])::text[])))
);


ALTER TABLE public.medicos OWNER TO access_manager;

--
-- Name: operadores; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.operadores (
    id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.operadores OWNER TO access_manager;

--
-- Name: pacientes; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.pacientes (
    id uuid NOT NULL,
    folio_paciente character varying(24) NOT NULL,
    nombre character varying(180),
    apellido_paterno character varying(180),
    apellido_materno character varying(180),
    celular character varying(40),
    fecha_nacimiento date,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    desactivado_en timestamp with time zone,
    marcado_borrado_en timestamp with time zone,
    nombre_preferido character varying(60),
    CONSTRAINT ck_pacientes_ck_pacientes_contacto_o_fecha_nacimiento CHECK (((celular IS NOT NULL) OR (fecha_nacimiento IS NOT NULL))),
    CONSTRAINT ck_pacientes_ck_pacientes_identidad_minima CHECK (((nombre_preferido IS NOT NULL) OR ((nombre IS NOT NULL) AND (apellido_paterno IS NOT NULL))))
);


ALTER TABLE public.pacientes OWNER TO access_manager;

--
-- Name: pantallas_turnos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.pantallas_turnos (
    id uuid NOT NULL,
    codigo_dispositivo character varying(120) NOT NULL,
    token_hash character varying(255),
    complejo_id uuid NOT NULL,
    piso_id uuid,
    cluster_espera_id uuid,
    consultorio_id uuid,
    nombre character varying(180),
    activa boolean DEFAULT true NOT NULL,
    ultima_conexion timestamp with time zone,
    polling_interval_seconds integer DEFAULT 5 NOT NULL,
    color_fondo character varying(40),
    color_texto character varying(40),
    color_turno_nuevo character varying(40),
    color_turno_normal character varying(40),
    font_size_turno_nuevo integer,
    font_size_turno_normal integer,
    segundos_resaltado integer DEFAULT 25 NOT NULL,
    segundos_visible integer DEFAULT 300 NOT NULL,
    max_turnos_visibles integer DEFAULT 10 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    descripcion text,
    CONSTRAINT ck_pantallas_turnos_ck_pantallas_turnos_max_turnos_visi_b64d CHECK (((max_turnos_visibles >= 1) AND (max_turnos_visibles <= 50))),
    CONSTRAINT ck_pantallas_turnos_ck_pantallas_turnos_polling_interval_range CHECK (((polling_interval_seconds >= 2) AND (polling_interval_seconds <= 10))),
    CONSTRAINT ck_pantallas_turnos_ck_pantallas_turnos_segundos_resalt_7436 CHECK (((segundos_resaltado >= 5) AND (segundos_resaltado <= 120))),
    CONSTRAINT ck_pantallas_turnos_ck_pantallas_turnos_segundos_visible_range CHECK (((segundos_visible >= 30) AND (segundos_visible <= 3600)))
);


ALTER TABLE public.pantallas_turnos OWNER TO access_manager;

--
-- Name: pantallas_turnos_clusters; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.pantallas_turnos_clusters (
    pantalla_id uuid NOT NULL,
    cluster_id uuid NOT NULL
);


ALTER TABLE public.pantallas_turnos_clusters OWNER TO access_manager;

--
-- Name: pisos; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.pisos (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    numero character varying(40) NOT NULL,
    nombre_visible character varying(180) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.pisos OWNER TO access_manager;

--
-- Name: puntos_acceso; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.puntos_acceso (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.puntos_acceso OWNER TO access_manager;

--
-- Name: qr_tokens; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.qr_tokens (
    id uuid NOT NULL,
    cita_id uuid NOT NULL,
    estado character varying(24) DEFAULT 'GENERADO'::character varying NOT NULL,
    token_hash character varying(128) NOT NULL,
    fecha_emision timestamp with time zone NOT NULL,
    fecha_expiracion timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_qr_tokens_ck_qr_tokens_estado_valido CHECK (((estado)::text = ANY ((ARRAY['GENERADO'::character varying, 'USADO'::character varying, 'EXPIRADO'::character varying, 'CANCELADO'::character varying])::text[])))
);


ALTER TABLE public.qr_tokens OWNER TO access_manager;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    codigo character varying(80) NOT NULL,
    nombre character varying(180) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO access_manager;

--
-- Name: salas_espera; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.salas_espera (
    id uuid NOT NULL,
    complejo_id uuid NOT NULL,
    piso_id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    descripcion text,
    capacidad_estimada integer,
    activa boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.salas_espera OWNER TO access_manager;

--
-- Name: turnos_display; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.turnos_display (
    id uuid NOT NULL,
    cita_id uuid,
    pantalla_id uuid,
    complejo_id uuid NOT NULL,
    piso_id uuid,
    cluster_espera_id uuid,
    consultorio_id uuid NOT NULL,
    turno character varying(40) NOT NULL,
    consultorio character varying(180) NOT NULL,
    estado character varying(20) DEFAULT 'NUEVO'::character varying NOT NULL,
    llamado_en timestamp with time zone NOT NULL,
    resaltado_hasta timestamp with time zone NOT NULL,
    visible_hasta timestamp with time zone NOT NULL,
    ocultado_en timestamp with time zone,
    llamado_por uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    texto_visible character varying(255),
    llamado_numero integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_turnos_display_ck_turnos_display_estado_valido CHECK (((estado)::text = ANY ((ARRAY['NUEVO'::character varying, 'VISIBLE'::character varying, 'OCULTO'::character varying, 'CANCELADO'::character varying])::text[])))
);


ALTER TABLE public.turnos_display OWNER TO access_manager;

--
-- Name: usuario_roles; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.usuario_roles (
    id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    rol_id uuid NOT NULL,
    institucion_id uuid,
    complejo_id uuid,
    activo boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.usuario_roles OWNER TO access_manager;

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: access_manager
--

CREATE TABLE public.usuarios (
    id uuid NOT NULL,
    nombre character varying(180) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(500) NOT NULL,
    telefono character varying(64),
    two_factor_enabled boolean DEFAULT false NOT NULL,
    estado character varying(32) DEFAULT 'ACTIVO'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    force_password_change boolean DEFAULT false NOT NULL
);


ALTER TABLE public.usuarios OWNER TO access_manager;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.alembic_version (version_num) FROM stdin;
202607190001
\.


--
-- Data for Name: asignaciones_medico_consultorio; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.asignaciones_medico_consultorio (id, medico_id, consultorio_id, fecha_inicio, fecha_fin, hora_inicio, hora_fin, dias_semana, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: asignaciones_operador; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.asignaciones_operador (id, operador_id, medico_id, consultorio_id, complejo_id, fecha_inicio, fecha_fin, prioridad, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.auditoria (id, evento, entidad, entidad_id, usuario_id, canal, ip_origen, valor_antes, valor_despues, created_at) FROM stdin;
\.


--
-- Data for Name: citas; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.citas (id, complejo_id, piso_id, cluster_espera_id, consultorio_id, estado, created_at, updated_at, tipo, paciente_id, medico_id, sala_prevista_id, fecha_cita, hora_cita, duracion_estimada, folio_turno, origen, notas_operativas, creada_por) FROM stdin;
\.


--
-- Data for Name: clusters_turnos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.clusters_turnos (id, complejo_id, piso_id, nombre, descripcion, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: complejos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.complejos (id, institucion_id, nombre, descripcion, logo_url, direccion, telefono, zona_horaria, color_primario, color_secundario, color_acento, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: consultorios; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.consultorios (id, complejo_id, piso_id, codigo, nombre_visible, instrucciones_acceso, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: consultorios_clusters; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.consultorios_clusters (consultorio_id, cluster_id) FROM stdin;
\.


--
-- Data for Name: contactos_institucionales; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.contactos_institucionales (id, nombre, medios_contacto, tipo_contacto, notas, created_at, updated_at, tipo_contacto_descripcion) FROM stdin;
\.


--
-- Data for Name: contactos_institucionales_complejos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.contactos_institucionales_complejos (contacto_id, complejo_id) FROM stdin;
\.


--
-- Data for Name: eventos_llegada; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.eventos_llegada (id, cita_id, tipo, sala_id, canal, usuario_id, dispositivo_id, ip_origen, created_at) FROM stdin;
\.


--
-- Data for Name: instituciones; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.instituciones (id, nombre, razon_social, logo_url, color_primario, color_secundario, color_acento, activo, created_at, updated_at, notas) FROM stdin;
\.


--
-- Data for Name: kioskos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.kioskos (id, codigo_dispositivo, token_hash, complejo_id, piso_id, punto_acceso_id, nombre, descripcion, activo, ultima_conexion, polling_interval_seconds, color_fondo, color_texto, color_primario, color_acento, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: medicos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.medicos (id, usuario_id, nombre, apellidos, nombre_visible, activo, created_at, updated_at, plantilla_turno) FROM stdin;
\.


--
-- Data for Name: operadores; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.operadores (id, usuario_id, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: pacientes; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.pacientes (id, folio_paciente, nombre, apellido_paterno, apellido_materno, celular, fecha_nacimiento, activo, created_at, updated_at, desactivado_en, marcado_borrado_en, nombre_preferido) FROM stdin;
\.


--
-- Data for Name: pantallas_turnos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.pantallas_turnos (id, codigo_dispositivo, token_hash, complejo_id, piso_id, cluster_espera_id, consultorio_id, nombre, activa, ultima_conexion, polling_interval_seconds, color_fondo, color_texto, color_turno_nuevo, color_turno_normal, font_size_turno_nuevo, font_size_turno_normal, segundos_resaltado, segundos_visible, max_turnos_visibles, created_at, updated_at, descripcion) FROM stdin;
\.


--
-- Data for Name: pantallas_turnos_clusters; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.pantallas_turnos_clusters (pantalla_id, cluster_id) FROM stdin;
\.


--
-- Data for Name: pisos; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.pisos (id, complejo_id, numero, nombre_visible, descripcion, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: puntos_acceso; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.puntos_acceso (id, complejo_id, piso_id, nombre, descripcion, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: qr_tokens; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.qr_tokens (id, cita_id, estado, token_hash, fecha_emision, fecha_expiracion, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.roles (id, codigo, nombre, descripcion, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: salas_espera; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.salas_espera (id, complejo_id, piso_id, nombre, descripcion, capacidad_estimada, activa, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: turnos_display; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.turnos_display (id, cita_id, pantalla_id, complejo_id, piso_id, cluster_espera_id, consultorio_id, turno, consultorio, estado, llamado_en, resaltado_hasta, visible_hasta, ocultado_en, llamado_por, created_at, updated_at, texto_visible, llamado_numero) FROM stdin;
\.


--
-- Data for Name: usuario_roles; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.usuario_roles (id, usuario_id, rol_id, institucion_id, complejo_id, activo, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: access_manager
--

COPY public.usuarios (id, nombre, email, password_hash, telefono, two_factor_enabled, estado, created_at, updated_at, force_password_change) FROM stdin;
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asignaciones_medico_consultorio pk_asignaciones_medico_consultorio; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_medico_consultorio
    ADD CONSTRAINT pk_asignaciones_medico_consultorio PRIMARY KEY (id);


--
-- Name: asignaciones_operador pk_asignaciones_operador; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_operador
    ADD CONSTRAINT pk_asignaciones_operador PRIMARY KEY (id);


--
-- Name: auditoria pk_auditoria; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT pk_auditoria PRIMARY KEY (id);


--
-- Name: citas pk_citas; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT pk_citas PRIMARY KEY (id);


--
-- Name: clusters_turnos pk_clusters_turnos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.clusters_turnos
    ADD CONSTRAINT pk_clusters_turnos PRIMARY KEY (id);


--
-- Name: complejos pk_complejos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.complejos
    ADD CONSTRAINT pk_complejos PRIMARY KEY (id);


--
-- Name: consultorios pk_consultorios; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios
    ADD CONSTRAINT pk_consultorios PRIMARY KEY (id);


--
-- Name: consultorios_clusters pk_consultorios_clusters; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios_clusters
    ADD CONSTRAINT pk_consultorios_clusters PRIMARY KEY (consultorio_id, cluster_id);


--
-- Name: contactos_institucionales pk_contactos_institucionales; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.contactos_institucionales
    ADD CONSTRAINT pk_contactos_institucionales PRIMARY KEY (id);


--
-- Name: contactos_institucionales_complejos pk_contactos_institucionales_complejos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.contactos_institucionales_complejos
    ADD CONSTRAINT pk_contactos_institucionales_complejos PRIMARY KEY (contacto_id, complejo_id);


--
-- Name: eventos_llegada pk_eventos_llegada; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.eventos_llegada
    ADD CONSTRAINT pk_eventos_llegada PRIMARY KEY (id);


--
-- Name: instituciones pk_instituciones; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.instituciones
    ADD CONSTRAINT pk_instituciones PRIMARY KEY (id);


--
-- Name: kioskos pk_kioskos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.kioskos
    ADD CONSTRAINT pk_kioskos PRIMARY KEY (id);


--
-- Name: medicos pk_medicos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.medicos
    ADD CONSTRAINT pk_medicos PRIMARY KEY (id);


--
-- Name: operadores pk_operadores; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.operadores
    ADD CONSTRAINT pk_operadores PRIMARY KEY (id);


--
-- Name: pacientes pk_pacientes; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pacientes
    ADD CONSTRAINT pk_pacientes PRIMARY KEY (id);


--
-- Name: pantallas_turnos pk_pantallas_turnos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos
    ADD CONSTRAINT pk_pantallas_turnos PRIMARY KEY (id);


--
-- Name: pantallas_turnos_clusters pk_pantallas_turnos_clusters; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos_clusters
    ADD CONSTRAINT pk_pantallas_turnos_clusters PRIMARY KEY (pantalla_id, cluster_id);


--
-- Name: pisos pk_pisos; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pisos
    ADD CONSTRAINT pk_pisos PRIMARY KEY (id);


--
-- Name: puntos_acceso pk_puntos_acceso; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.puntos_acceso
    ADD CONSTRAINT pk_puntos_acceso PRIMARY KEY (id);


--
-- Name: qr_tokens pk_qr_tokens; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.qr_tokens
    ADD CONSTRAINT pk_qr_tokens PRIMARY KEY (id);


--
-- Name: roles pk_roles; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT pk_roles PRIMARY KEY (id);


--
-- Name: salas_espera pk_salas_espera; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.salas_espera
    ADD CONSTRAINT pk_salas_espera PRIMARY KEY (id);


--
-- Name: turnos_display pk_turnos_display; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT pk_turnos_display PRIMARY KEY (id);


--
-- Name: usuario_roles pk_usuario_roles; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT pk_usuario_roles PRIMARY KEY (id);


--
-- Name: usuarios pk_usuarios; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT pk_usuarios PRIMARY KEY (id);


--
-- Name: citas uq_citas_complejo_fecha_folio; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT uq_citas_complejo_fecha_folio UNIQUE (complejo_id, fecha_cita, folio_turno);


--
-- Name: clusters_turnos uq_clusters_turnos_piso_nombre; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.clusters_turnos
    ADD CONSTRAINT uq_clusters_turnos_piso_nombre UNIQUE (piso_id, nombre);


--
-- Name: consultorios uq_consultorios_complejo_codigo; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios
    ADD CONSTRAINT uq_consultorios_complejo_codigo UNIQUE (complejo_id, codigo);


--
-- Name: kioskos uq_kioskos_codigo_dispositivo; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.kioskos
    ADD CONSTRAINT uq_kioskos_codigo_dispositivo UNIQUE (codigo_dispositivo);


--
-- Name: pacientes uq_pacientes_folio_paciente; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pacientes
    ADD CONSTRAINT uq_pacientes_folio_paciente UNIQUE (folio_paciente);


--
-- Name: pantallas_turnos uq_pantallas_turnos_codigo_dispositivo; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos
    ADD CONSTRAINT uq_pantallas_turnos_codigo_dispositivo UNIQUE (codigo_dispositivo);


--
-- Name: puntos_acceso uq_puntos_acceso_piso_nombre; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.puntos_acceso
    ADD CONSTRAINT uq_puntos_acceso_piso_nombre UNIQUE (piso_id, nombre);


--
-- Name: roles uq_roles_codigo; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT uq_roles_codigo UNIQUE (codigo);


--
-- Name: usuarios uq_usuarios_email; Type: CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT uq_usuarios_email UNIQUE (email);


--
-- Name: ix_asignaciones_medico_consultorio_consultorio_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_medico_consultorio_consultorio_id ON public.asignaciones_medico_consultorio USING btree (consultorio_id);


--
-- Name: ix_asignaciones_medico_consultorio_medico_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_medico_consultorio_medico_id ON public.asignaciones_medico_consultorio USING btree (medico_id);


--
-- Name: ix_asignaciones_operador_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_operador_complejo_id ON public.asignaciones_operador USING btree (complejo_id);


--
-- Name: ix_asignaciones_operador_consultorio_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_operador_consultorio_id ON public.asignaciones_operador USING btree (consultorio_id);


--
-- Name: ix_asignaciones_operador_medico_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_operador_medico_id ON public.asignaciones_operador USING btree (medico_id);


--
-- Name: ix_asignaciones_operador_operador_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_asignaciones_operador_operador_id ON public.asignaciones_operador USING btree (operador_id);


--
-- Name: ix_auditoria_created_at; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_auditoria_created_at ON public.auditoria USING btree (created_at);


--
-- Name: ix_auditoria_entidad; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_auditoria_entidad ON public.auditoria USING btree (entidad, entidad_id);


--
-- Name: ix_citas_cluster_espera_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_cluster_espera_id ON public.citas USING btree (cluster_espera_id);


--
-- Name: ix_citas_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_complejo_id ON public.citas USING btree (complejo_id);


--
-- Name: ix_citas_consultorio_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_consultorio_id ON public.citas USING btree (consultorio_id);


--
-- Name: ix_citas_creada_por; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_creada_por ON public.citas USING btree (creada_por);


--
-- Name: ix_citas_fecha_cita; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_fecha_cita ON public.citas USING btree (fecha_cita);


--
-- Name: ix_citas_medico_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_medico_id ON public.citas USING btree (medico_id);


--
-- Name: ix_citas_paciente_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_paciente_id ON public.citas USING btree (paciente_id);


--
-- Name: ix_citas_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_piso_id ON public.citas USING btree (piso_id);


--
-- Name: ix_citas_sala_prevista_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_citas_sala_prevista_id ON public.citas USING btree (sala_prevista_id);


--
-- Name: ix_clusters_turnos_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_clusters_turnos_complejo_id ON public.clusters_turnos USING btree (complejo_id);


--
-- Name: ix_clusters_turnos_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_clusters_turnos_piso_id ON public.clusters_turnos USING btree (piso_id);


--
-- Name: ix_complejos_institucion_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_complejos_institucion_id ON public.complejos USING btree (institucion_id);


--
-- Name: ix_consultorios_clusters_cluster_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_consultorios_clusters_cluster_id ON public.consultorios_clusters USING btree (cluster_id);


--
-- Name: ix_consultorios_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_consultorios_complejo_id ON public.consultorios USING btree (complejo_id);


--
-- Name: ix_consultorios_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_consultorios_piso_id ON public.consultorios USING btree (piso_id);


--
-- Name: ix_eventos_llegada_cita_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_eventos_llegada_cita_id ON public.eventos_llegada USING btree (cita_id);


--
-- Name: ix_eventos_llegada_sala_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_eventos_llegada_sala_id ON public.eventos_llegada USING btree (sala_id);


--
-- Name: ix_eventos_llegada_usuario_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_eventos_llegada_usuario_id ON public.eventos_llegada USING btree (usuario_id);


--
-- Name: ix_kioskos_codigo_dispositivo; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_kioskos_codigo_dispositivo ON public.kioskos USING btree (codigo_dispositivo);


--
-- Name: ix_kioskos_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_kioskos_complejo_id ON public.kioskos USING btree (complejo_id);


--
-- Name: ix_kioskos_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_kioskos_piso_id ON public.kioskos USING btree (piso_id);


--
-- Name: ix_kioskos_punto_acceso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_kioskos_punto_acceso_id ON public.kioskos USING btree (punto_acceso_id);


--
-- Name: ix_medicos_usuario_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_medicos_usuario_id ON public.medicos USING btree (usuario_id);


--
-- Name: ix_operadores_usuario_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_operadores_usuario_id ON public.operadores USING btree (usuario_id);


--
-- Name: ix_pacientes_celular; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pacientes_celular ON public.pacientes USING btree (celular);


--
-- Name: ix_pacientes_folio_paciente; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pacientes_folio_paciente ON public.pacientes USING btree (folio_paciente);


--
-- Name: ix_pantallas_turnos_cluster_espera_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_cluster_espera_id ON public.pantallas_turnos USING btree (cluster_espera_id);


--
-- Name: ix_pantallas_turnos_clusters_cluster_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_clusters_cluster_id ON public.pantallas_turnos_clusters USING btree (cluster_id);


--
-- Name: ix_pantallas_turnos_codigo_dispositivo; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_codigo_dispositivo ON public.pantallas_turnos USING btree (codigo_dispositivo);


--
-- Name: ix_pantallas_turnos_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_complejo_id ON public.pantallas_turnos USING btree (complejo_id);


--
-- Name: ix_pantallas_turnos_consultorio_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_consultorio_id ON public.pantallas_turnos USING btree (consultorio_id);


--
-- Name: ix_pantallas_turnos_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pantallas_turnos_piso_id ON public.pantallas_turnos USING btree (piso_id);


--
-- Name: ix_pisos_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_pisos_complejo_id ON public.pisos USING btree (complejo_id);


--
-- Name: ix_puntos_acceso_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_puntos_acceso_complejo_id ON public.puntos_acceso USING btree (complejo_id);


--
-- Name: ix_puntos_acceso_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_puntos_acceso_piso_id ON public.puntos_acceso USING btree (piso_id);


--
-- Name: ix_qr_tokens_cita_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_qr_tokens_cita_id ON public.qr_tokens USING btree (cita_id);


--
-- Name: ix_qr_tokens_token_hash; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_qr_tokens_token_hash ON public.qr_tokens USING btree (token_hash);


--
-- Name: ix_roles_codigo; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_roles_codigo ON public.roles USING btree (codigo);


--
-- Name: ix_salas_espera_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_salas_espera_complejo_id ON public.salas_espera USING btree (complejo_id);


--
-- Name: ix_salas_espera_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_salas_espera_piso_id ON public.salas_espera USING btree (piso_id);


--
-- Name: ix_turnos_display_cita_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_cita_id ON public.turnos_display USING btree (cita_id);


--
-- Name: ix_turnos_display_cluster_espera_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_cluster_espera_id ON public.turnos_display USING btree (cluster_espera_id);


--
-- Name: ix_turnos_display_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_complejo_id ON public.turnos_display USING btree (complejo_id);


--
-- Name: ix_turnos_display_consultorio_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_consultorio_id ON public.turnos_display USING btree (consultorio_id);


--
-- Name: ix_turnos_display_llamado_en; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_llamado_en ON public.turnos_display USING btree (llamado_en);


--
-- Name: ix_turnos_display_llamado_por; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_llamado_por ON public.turnos_display USING btree (llamado_por);


--
-- Name: ix_turnos_display_pantalla_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_pantalla_id ON public.turnos_display USING btree (pantalla_id);


--
-- Name: ix_turnos_display_piso_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_turnos_display_piso_id ON public.turnos_display USING btree (piso_id);


--
-- Name: ix_usuario_roles_complejo_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_usuario_roles_complejo_id ON public.usuario_roles USING btree (complejo_id);


--
-- Name: ix_usuario_roles_institucion_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_usuario_roles_institucion_id ON public.usuario_roles USING btree (institucion_id);


--
-- Name: ix_usuario_roles_rol_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_usuario_roles_rol_id ON public.usuario_roles USING btree (rol_id);


--
-- Name: ix_usuario_roles_usuario_id; Type: INDEX; Schema: public; Owner: access_manager
--

CREATE INDEX ix_usuario_roles_usuario_id ON public.usuario_roles USING btree (usuario_id);


--
-- Name: asignaciones_medico_consultorio fk_asignaciones_medico_consultorio_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_medico_consultorio
    ADD CONSTRAINT fk_asignaciones_medico_consultorio_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id);


--
-- Name: asignaciones_medico_consultorio fk_asignaciones_medico_consultorio_medico_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_medico_consultorio
    ADD CONSTRAINT fk_asignaciones_medico_consultorio_medico_id FOREIGN KEY (medico_id) REFERENCES public.medicos(id);


--
-- Name: asignaciones_operador fk_asignaciones_operador_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_operador
    ADD CONSTRAINT fk_asignaciones_operador_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: asignaciones_operador fk_asignaciones_operador_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_operador
    ADD CONSTRAINT fk_asignaciones_operador_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id);


--
-- Name: asignaciones_operador fk_asignaciones_operador_medico_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_operador
    ADD CONSTRAINT fk_asignaciones_operador_medico_id FOREIGN KEY (medico_id) REFERENCES public.medicos(id);


--
-- Name: asignaciones_operador fk_asignaciones_operador_operador_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.asignaciones_operador
    ADD CONSTRAINT fk_asignaciones_operador_operador_id FOREIGN KEY (operador_id) REFERENCES public.operadores(id);


--
-- Name: auditoria fk_auditoria_usuario_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT fk_auditoria_usuario_id FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: citas fk_citas_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: citas fk_citas_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id);


--
-- Name: citas fk_citas_creada_por_usuarios; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_creada_por_usuarios FOREIGN KEY (creada_por) REFERENCES public.usuarios(id);


--
-- Name: citas fk_citas_medico_id_medicos; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_medico_id_medicos FOREIGN KEY (medico_id) REFERENCES public.medicos(id);


--
-- Name: citas fk_citas_paciente_id_pacientes; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_paciente_id_pacientes FOREIGN KEY (paciente_id) REFERENCES public.pacientes(id);


--
-- Name: citas fk_citas_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: citas fk_citas_sala_prevista_id_salas_espera; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT fk_citas_sala_prevista_id_salas_espera FOREIGN KEY (sala_prevista_id) REFERENCES public.salas_espera(id);


--
-- Name: clusters_turnos fk_clusters_turnos_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.clusters_turnos
    ADD CONSTRAINT fk_clusters_turnos_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: clusters_turnos fk_clusters_turnos_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.clusters_turnos
    ADD CONSTRAINT fk_clusters_turnos_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: complejos fk_complejos_institucion_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.complejos
    ADD CONSTRAINT fk_complejos_institucion_id FOREIGN KEY (institucion_id) REFERENCES public.instituciones(id);


--
-- Name: consultorios_clusters fk_consultorios_clusters_cluster_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios_clusters
    ADD CONSTRAINT fk_consultorios_clusters_cluster_id FOREIGN KEY (cluster_id) REFERENCES public.clusters_turnos(id) ON DELETE CASCADE;


--
-- Name: consultorios_clusters fk_consultorios_clusters_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios_clusters
    ADD CONSTRAINT fk_consultorios_clusters_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id) ON DELETE CASCADE;


--
-- Name: consultorios fk_consultorios_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios
    ADD CONSTRAINT fk_consultorios_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: consultorios fk_consultorios_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.consultorios
    ADD CONSTRAINT fk_consultorios_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: contactos_institucionales_complejos fk_contacto_complejo_complejo; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.contactos_institucionales_complejos
    ADD CONSTRAINT fk_contacto_complejo_complejo FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: contactos_institucionales_complejos fk_contacto_complejo_contacto; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.contactos_institucionales_complejos
    ADD CONSTRAINT fk_contacto_complejo_contacto FOREIGN KEY (contacto_id) REFERENCES public.contactos_institucionales(id) ON DELETE CASCADE;


--
-- Name: eventos_llegada fk_eventos_llegada_cita_id_citas; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.eventos_llegada
    ADD CONSTRAINT fk_eventos_llegada_cita_id_citas FOREIGN KEY (cita_id) REFERENCES public.citas(id);


--
-- Name: eventos_llegada fk_eventos_llegada_sala_id_salas_espera; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.eventos_llegada
    ADD CONSTRAINT fk_eventos_llegada_sala_id_salas_espera FOREIGN KEY (sala_id) REFERENCES public.salas_espera(id);


--
-- Name: eventos_llegada fk_eventos_llegada_usuario_id_usuarios; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.eventos_llegada
    ADD CONSTRAINT fk_eventos_llegada_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: kioskos fk_kioskos_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.kioskos
    ADD CONSTRAINT fk_kioskos_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: kioskos fk_kioskos_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.kioskos
    ADD CONSTRAINT fk_kioskos_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: kioskos fk_kioskos_punto_acceso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.kioskos
    ADD CONSTRAINT fk_kioskos_punto_acceso_id FOREIGN KEY (punto_acceso_id) REFERENCES public.puntos_acceso(id);


--
-- Name: medicos fk_medicos_usuario_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.medicos
    ADD CONSTRAINT fk_medicos_usuario_id FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: operadores fk_operadores_usuario_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.operadores
    ADD CONSTRAINT fk_operadores_usuario_id FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: pantallas_turnos_clusters fk_pantallas_turnos_clusters_cluster_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos_clusters
    ADD CONSTRAINT fk_pantallas_turnos_clusters_cluster_id FOREIGN KEY (cluster_id) REFERENCES public.clusters_turnos(id) ON DELETE CASCADE;


--
-- Name: pantallas_turnos_clusters fk_pantallas_turnos_clusters_pantalla_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos_clusters
    ADD CONSTRAINT fk_pantallas_turnos_clusters_pantalla_id FOREIGN KEY (pantalla_id) REFERENCES public.pantallas_turnos(id) ON DELETE CASCADE;


--
-- Name: pantallas_turnos fk_pantallas_turnos_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos
    ADD CONSTRAINT fk_pantallas_turnos_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: pantallas_turnos fk_pantallas_turnos_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos
    ADD CONSTRAINT fk_pantallas_turnos_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id);


--
-- Name: pantallas_turnos fk_pantallas_turnos_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pantallas_turnos
    ADD CONSTRAINT fk_pantallas_turnos_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: pisos fk_pisos_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.pisos
    ADD CONSTRAINT fk_pisos_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: puntos_acceso fk_puntos_acceso_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.puntos_acceso
    ADD CONSTRAINT fk_puntos_acceso_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: puntos_acceso fk_puntos_acceso_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.puntos_acceso
    ADD CONSTRAINT fk_puntos_acceso_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: qr_tokens fk_qr_tokens_cita_id_citas; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.qr_tokens
    ADD CONSTRAINT fk_qr_tokens_cita_id_citas FOREIGN KEY (cita_id) REFERENCES public.citas(id);


--
-- Name: salas_espera fk_salas_espera_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.salas_espera
    ADD CONSTRAINT fk_salas_espera_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: salas_espera fk_salas_espera_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.salas_espera
    ADD CONSTRAINT fk_salas_espera_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: turnos_display fk_turnos_display_cita_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_cita_id FOREIGN KEY (cita_id) REFERENCES public.citas(id);


--
-- Name: turnos_display fk_turnos_display_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: turnos_display fk_turnos_display_consultorio_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_consultorio_id FOREIGN KEY (consultorio_id) REFERENCES public.consultorios(id);


--
-- Name: turnos_display fk_turnos_display_llamado_por; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_llamado_por FOREIGN KEY (llamado_por) REFERENCES public.usuarios(id);


--
-- Name: turnos_display fk_turnos_display_pantalla_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_pantalla_id FOREIGN KEY (pantalla_id) REFERENCES public.pantallas_turnos(id);


--
-- Name: turnos_display fk_turnos_display_piso_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.turnos_display
    ADD CONSTRAINT fk_turnos_display_piso_id FOREIGN KEY (piso_id) REFERENCES public.pisos(id);


--
-- Name: usuario_roles fk_usuario_roles_complejo_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT fk_usuario_roles_complejo_id FOREIGN KEY (complejo_id) REFERENCES public.complejos(id);


--
-- Name: usuario_roles fk_usuario_roles_institucion_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT fk_usuario_roles_institucion_id FOREIGN KEY (institucion_id) REFERENCES public.instituciones(id);


--
-- Name: usuario_roles fk_usuario_roles_rol_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT fk_usuario_roles_rol_id FOREIGN KEY (rol_id) REFERENCES public.roles(id);


--
-- Name: usuario_roles fk_usuario_roles_usuario_id; Type: FK CONSTRAINT; Schema: public; Owner: access_manager
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT fk_usuario_roles_usuario_id FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- PostgreSQL database dump complete
--

\unrestrict xiSg355ILmL7XnppJQdKwV4BKRrtgvB0bsdnONUUXmgHHiQD7pXrwDD3kDvG8EK

