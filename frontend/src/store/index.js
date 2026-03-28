import { createStore } from 'vuex'
import auth from './modules/auth'
import podcasts from './modules/podcasts'
import episodes from './modules/episodes'
import player from './modules/player'

export default createStore({
  modules: {
    auth,
    podcasts,
    episodes,
    player,
  },

  state: {
    appLoading: false,
    globalError: null,
    sidebarOpen: true,
  },

  mutations: {
    SET_APP_LOADING(state, loading) {
      state.appLoading = loading
    },
    SET_GLOBAL_ERROR(state, error) {
      state.globalError = error
    },
    CLEAR_GLOBAL_ERROR(state) {
      state.globalError = null
    },
    TOGGLE_SIDEBAR(state) {
      state.sidebarOpen = !state.sidebarOpen
    },
  },

  actions: {
    setLoading({ commit }, loading) {
      commit('SET_APP_LOADING', loading)
    },
    setError({ commit }, error) {
      commit('SET_GLOBAL_ERROR', error)
      setTimeout(() => commit('CLEAR_GLOBAL_ERROR'), 5000)
    },
  },

  getters: {
    isLoading: (state) => state.appLoading,
    globalError: (state) => state.globalError,
  },
})
