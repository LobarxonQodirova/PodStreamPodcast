<template>
  <div id="app" class="min-h-screen flex flex-col bg-gray-50">
    <Navbar />
    <div class="flex flex-1">
      <Sidebar v-if="showSidebar" />
      <main class="flex-1 p-6 pb-32" :class="{ 'ml-64': showSidebar }">
        <router-view />
      </main>
    </div>
    <AudioPlayer v-if="currentEpisode" />
    <Footer v-if="!currentEpisode" />
  </div>
</template>

<script>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { useRoute } from 'vue-router'
import Navbar from './components/common/Navbar.vue'
import Sidebar from './components/common/Sidebar.vue'
import Footer from './components/common/Footer.vue'
import AudioPlayer from './components/common/AudioPlayer.vue'

export default {
  name: 'App',
  components: { Navbar, Sidebar, Footer, AudioPlayer },
  setup() {
    const store = useStore()
    const route = useRoute()

    const currentEpisode = computed(() => store.state.player.currentEpisode)
    const showSidebar = computed(() => {
      const hiddenRoutes = ['login', 'register']
      return !hiddenRoutes.includes(route.name)
    })

    return { currentEpisode, showSidebar }
  },
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f5f9;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
