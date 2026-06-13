import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import HomePage from './pages/HomePage.vue'
import VideoDetectionPage from './pages/VideoDetectionPage.vue'
import GuidePage from './pages/GuidePage.vue'
import ProfilePage from './pages/ProfilePage.vue'
import './styles.css'

const routes = [
  { path: '/', component: HomePage },
  { path: '/video-detection', component: VideoDetectionPage },
  { path: '/guide', component: GuidePage },
  { path: '/profile', component: ProfilePage }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

createApp(App).use(router).mount('#app')
