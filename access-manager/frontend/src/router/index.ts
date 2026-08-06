import { createRouter, createWebHistory } from 'vue-router';
import { clearToken, getCurrentUser, getToken } from '../api/client';
import LoginView from '../views/LoginView.vue';
import DashboardView from '../views/DashboardView.vue';
import InstitucionesView from '../views/InstitucionesView.vue';
import ComplejosView from '../views/ComplejosView.vue';
import CatalogView from '../views/CatalogView.vue';
import RolesView from '../views/RolesView.vue';
import UsuariosView from '../views/UsuariosView.vue';
import UsuarioRolesView from '../views/UsuarioRolesView.vue';
import PerfilView from '../views/PerfilView.vue';
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
import ConsultaClustersConsultoriosView from '../views/ConsultaClustersConsultoriosView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginView, meta: { public: true } },
    {
      path: '/display/:codigo_dispositivo',
      component: DisplayTurnosView,
      meta: { public: true, fullscreen: true, hideUserBadge: true },
    },
    { path: '/dashboard', component: DashboardView },
    { path: '/perfil', component: PerfilView },
    { path: '/instituciones', component: InstitucionesView },
    { path: '/complejos', component: ComplejosView },
    { path: '/usuarios', component: UsuariosView },
    { path: '/roles', component: RolesView },
    { path: '/usuario-roles', component: UsuarioRolesView },
    { path: '/torres', component: CatalogView, meta: { catalog: 'torres' } },
    { path: '/pisos', component: CatalogView, meta: { catalog: 'pisos' } },
    { path: '/salas-espera', component: CatalogView, meta: { catalog: 'salas-espera' } },
    { path: '/clusters-turnos', component: CatalogView, meta: { catalog: 'clusters-turnos' } },
    { path: '/consultorios', component: CatalogView, meta: { catalog: 'consultorios' } },
    { path: '/consulta-clusters-consultorios', component: ConsultaClustersConsultoriosView },
    { path: '/medicos', component: CatalogView, meta: { catalog: 'medicos' } },
    { path: '/operadores', component: CatalogView, meta: { catalog: 'operadores' } },
    { path: '/pantallas-turnos', component: PantallasTurnosView, meta: { hideUserBadge: true } },
    { path: '/kioskos', component: KioskosView, meta: { hideUserBadge: true } },
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

router.beforeEach(async (to) => {
  const token = getToken();
  if (!to.meta.public && !token) {
    return '/login';
  }
  if (!token || (to.meta.public && to.path !== '/login')) {
    return;
  }

  try {
    const user = await getCurrentUser();
    if (user.force_password_change && to.path !== '/perfil') {
      return '/perfil';
    }
    if (to.path === '/login') {
      return user.force_password_change ? '/perfil' : '/dashboard';
    }
  } catch {
    clearToken();
    if (!to.meta.public) {
      return '/login';
    }
  }
});

export default router;
