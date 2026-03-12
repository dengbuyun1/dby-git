import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Choose from '@/views/Choose.vue'
import TruePatientsMonitor from '@/views/TruePatientsMonitor.vue'
import VPatientsMonitor from '@/views/VPatientsMonitor.vue'
import TotalPatientsList from '@/views/TotalPatientsList.vue'
import SimulationsList from '@/views/SimulationsList.vue'
import DigitalTwin from '@/views/DigitalTwin.vue'
import TestSimulation from '@/views/TestSimulation.vue'

const routes = [
	{
		path: '/',
		redirect: '/login'
	},
	{
		path: '/login',
		name: 'Login',
		component: Login
	},
	{
		path: '/choose',
		name: 'Choose',
		component: Choose,
		meta: { requiresAuth: true }
	},
	{
		path: '/digital-twin',
		name: 'DigitalTwin',
		component: DigitalTwin,
		meta: { requiresAuth: true }
	},
	{
		path: '/true-patients-monitor/:patientId?',
		name: 'TruePatientsMonitor',
		component: TruePatientsMonitor,
		meta: { requiresAuth: true }
	},
	{
		path: '/v-patients-monitor/:patientId?',
		name: 'VPatientsMonitor',
		component: VPatientsMonitor,
		meta: { requiresAuth: true }
	},
	{
		path: '/patients-list',
		name: 'TotalPatientsList',
		component: TotalPatientsList,
		meta: { requiresAuth: true }
	},
	{
		path: '/simulations-list',
		name: 'SimulationsList',
		component: SimulationsList,
		meta: { requiresAuth: true }
	},
	{
		path: '/test-simulation',
		name: 'TestSimulation',
		component: TestSimulation,
		meta: { requiresAuth: true }
	}
]

const router = createRouter({
	history: createWebHistory(),
	routes
})

// 路由守卫 - 检查登录状态
router.beforeEach((to, from, next) => {
	const isLoggedIn = localStorage.getItem('userToken')

	if (to.meta.requiresAuth && !isLoggedIn) {
		next('/login')
	} else {
		next()
	}
})

export default router