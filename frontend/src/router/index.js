import { createRouter, createWebHistory } from 'vue-router'
import store from '../store'

import HomeView from '../views/HomeView.vue'
import DiscoverView from '../views/DiscoverView.vue'
import PodcastView from '../views/PodcastView.vue'
import EpisodeView from '../views/EpisodeView.vue'
import StudioView from '../views/StudioView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { title: 'Home' },
  },
  {
    path: '/discover',
    name: 'discover',
    component: DiscoverView,
    meta: { title: 'Discover Podcasts' },
  },
  {
    path: '/podcast/:slug',
    name: 'podcast',
    component: PodcastView,
    meta: { title: 'Podcast' },
    props: true,
  },
  {
    path: '/podcast/:podcastSlug/episode/:episodeSlug',
    name: 'episode',
    component: EpisodeView,
    meta: { title: 'Episode' },
    props: true,
  },
  {
    path: '/studio',
    name: 'studio',
    component: StudioView,
    meta: { title: 'Creator Studio', requiresAuth: true, requiresPodcaster: true },
  },
  {
    path: '/analytics',
    name: 'analytics',
    component: AnalyticsView,
    meta: { title: 'Analytics', requiresAuth: true, requiresPodcaster: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/HomeView.vue'),
    meta: { title: 'Log In', guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/HomeView.vue'),
    meta: { title: 'Sign Up', guest: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: {
      template: `
        <div class="flex items-center justify-center min-h-[60vh]">
          <div class="text-center">
            <h1 class="text-6xl font-bold text-indigo-600 mb-4">404</h1>
            <p class="text-xl text-gray-600 mb-6">Page not found</p>
            <router-link to="/" class="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition">
              Go Home
            </router-link>
          </div>
        </div>
      `,
    },
    meta: { title: 'Not Found' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

// Navigation guards
router.beforeEach((to, from, next) => {
  // Set page title
  document.title = to.meta.title
    ? `${to.meta.title} | PodStream`
    : 'PodStream'

  const isAuthenticated = store.getters['auth/isAuthenticated']
  const user = store.state.auth.user

  // Auth-required routes
  if (to.meta.requiresAuth && !isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  // Podcaster-required routes
  if (to.meta.requiresPodcaster && user && !['podcaster', 'admin'].includes(user.role)) {
    return next({ name: 'home' })
  }

  // Guest-only routes (login, register)
  if (to.meta.guest && isAuthenticated) {
    return next({ name: 'home' })
  }

  next()
})

export default router
