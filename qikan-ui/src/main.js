import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import './assets/theme.css'
import { useAudioStore } from './stores/audio'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

const audioStore = useAudioStore(pinia)
audioStore.init()

app.mount('#app')
