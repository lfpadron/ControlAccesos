import { createRouter, createWebHistory } from 'vue-router';
import { getToken } from '../api/client';
import LoginView from '../views/LoginView.vue';
import DashboardView from '../views/DashboardView.vue';
import InstitucionesView from '../views/InstitucionesView.vue';
import ComplejosView from '../views/ComplejosView.vue';
import CatalogView from '../views/CatalogView.vue';
import AsignacionesView from '../views/AsignacionesView.vue';
import AuditoriaView from '../views/AuditoriaView.vue';
import DisplayTurnosView from '../views/DisplayTurnosView.vue';
import TurnosLlamadosView from '../views/TurnosLlamadosView.vue';
import PacientesView from '../views/PacientesView.vue';
import CitasView from '../views/CitasView.vue';
import CitasHoyView from '../views/CitasHoyView.vue';
import PantallasTurnosView from '../views/PantallasTurnosView.vue';
import ContactosInstitucionalesView from '../views/ContactosInstitucionalesView.vue';
import ReportesView from '../views/ReportesView.vue';
import BusquedaUsuariosView from '../views/BusquedaUsuariosView.vue';
import KioskosView from '../views/KioskosView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginView, meta: { public: true } },
    {
      path: '/display/:codigo_dispositivo',
      component: DisplayTurnosView,
      meta: { public: true, fullscreen: true },
    },
    { path: '/dashboard', component: DashboardView },
    { path: '/instituciones', component: InstitucionesView },
    { path: '/complejos', component: ComplejosView },
    { path: '/usuarios', component: CatalogView, meta: { catalog: 'usuarios' } },
    { path: '/roles', component: CatalogView, meta: { catalog: 'roles' } },
    { path: '/usuario-roles', component: CatalogView, meta: { catalog: 'usuario-roles' } },
    { path: '/pisos', component: CatalogView, meta: { catalog: 'pisos' } },
    { path: '/salas-espera', component: CatalogView, meta: { catalog: 'salas-espera' } },
    { path: '/clusters-turnos', component: CatalogView, meta: { catalog: 'clusters-turnos' } },
    { path: '/consultorios', component: CatalogView, meta: { catalog: 'consultorios' } },
    { path: '/medicos', component: CatalogView, meta: { catalog: 'medicos' } },
    { path: '/operadores', component: CatalogView, meta: { catalog: 'operadores' } },
    { path: '/pantallas-turnos', component: PantallasTurnosView },
    { path: '/kioskos', component: KioskosView },
    { path: '/pacientes', component: PacientesView },
    { path: '/citas', component: CitasView },
    { path: '/citas/hoy', component: CitasHoyView },
    { path: '/busqueda-usuarios', component: BusquedaUsuariosView },
    { path: '/reportes', component: ReportesView },
    { path: '/contactos-institucionales', component: ContactosInstitucionalesView },
    { path: '/asignaciones', component: AsignacionesView },
    { path: '/turnos-llamados', component: TurnosLlamadosView },
    { path: '/auditoria', component: AuditoriaView },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !getToken()) {
    return '/login';
  }
  if (to.path === '/login' && getToken()) {
    return '/dashboard';
  }
});

export default router;
