<template>
  <div class="login-container">
    <div class="login-background">
      <div class="bg-pattern"></div>
    </div>
    
    <div class="login-box">
      <div class="logo-section">
        <div class="sword-icon">⚔️</div>
        <h1 class="title">骑砍英雄传</h1>
        <p class="subtitle">MOUNT & BLADE</p>
      </div>
      
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="⚔️ 登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input 
                v-model="loginForm.name" 
                placeholder="角色名" 
                maxlength="12"
                prefix-icon="👤"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-input 
                v-model="loginForm.password" 
                type="password" 
                placeholder="密码" 
                show-password
                prefix-icon="🔑"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-input 
                v-model="loginForm.adminKey" 
                type="password" 
                placeholder="访问密码（管理员设置）" 
                show-password
                prefix-icon="⚙️"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-button 
                type="danger" 
                :loading="loading" 
                @click="handleLogin" 
                size="large"
                class="login-btn"
              >
                ⚔️ 开始征程
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="📜 注册" name="register">
          <el-form :model="registerForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input 
                v-model="registerForm.name" 
                placeholder="角色名" 
                maxlength="12"
                prefix-icon="👤"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-input 
                v-model="registerForm.password" 
                type="password" 
                placeholder="密码" 
                show-password
                prefix-icon="🔑"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-input 
                v-model="registerForm.accessPassword" 
                type="password" 
                placeholder="访问密码（需要时填写）" 
                show-password
                prefix-icon="⚙️"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary"
                :loading="loading" 
                @click="handleRegister" 
                size="large"
                class="login-btn register-btn"
              >
                📜 创建角色
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <div class="footer-note">
        <p>在卡拉迪亚大陆展开你的传奇</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()

const activeTab = ref('login')
const loading = ref(false)

const loginForm = reactive({ name: '', password: '', adminKey: '' })
const registerForm = reactive({ name: '', password: '', accessPassword: '' })

const handleLogin = async () => {
  if (!loginForm.name || !loginForm.password) {
    ElMessage.warning('请输入角色名和密码')
    return
  }
  loading.value = true
  const success = await gameStore.login(loginForm.name, loginForm.password, loginForm.adminKey)
  loading.value = false
  if (success) {
    router.push('/home')
  }
}

const handleRegister = async () => {
  if (!registerForm.name || !registerForm.password) {
    ElMessage.warning('请输入角色名和密码')
    return
  }
  loading.value = true
  await gameStore.register(registerForm.name, registerForm.password, registerForm.accessPassword)
  loading.value = false
  activeTab.value = 'login'
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #0D0D0D 0%, #1A1A1A 50%, #0D0D0D 100%);
  z-index: 0;
}

.bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(139, 0, 0, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(212, 175, 55, 0.05) 0%, transparent 50%),
    url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%233D3D3D' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.8;
}

.login-box {
  position: relative;
  z-index: 1;
  width: 400px;
  padding: 48px 40px;
  background: linear-gradient(145deg, rgba(30, 30, 30, 0.95) 0%, rgba(20, 20, 20, 0.98) 100%);
  border-radius: 16px;
  border: 2px solid #3D3D3D;
  box-shadow: 
    0 0 60px rgba(0, 0, 0, 0.8),
    0 0 40px rgba(139, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.login-box::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, #8B0000, #D4AF37, #8B0000);
  border-radius: 18px;
  z-index: -1;
  opacity: 0.3;
}

.logo-section {
  text-align: center;
  margin-bottom: 32px;
}

.sword-icon {
  font-size: 48px;
  margin-bottom: 12px;
  filter: drop-shadow(0 0 20px rgba(212, 175, 55, 0.5));
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.title {
  text-align: center;
  color: #FFD700;
  margin: 0 0 8px;
  font-size: 32px;
  font-weight: bold;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8), 0 0 20px rgba(255, 215, 0, 0.3);
  letter-spacing: 4px;
}

.subtitle {
  text-align: center;
  color: #8B7355;
  margin: 0;
  font-size: 14px;
  letter-spacing: 6px;
  font-weight: 500;
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #3D3D3D;
}

.login-tabs :deep(.el-tabs__item) {
  color: #888;
  font-size: 16px;
  font-weight: bold;
  padding: 0 24px;
}

.login-tabs :deep(.el-tabs__item:hover) {
  color: #D4AF37;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: #FFD700;
}

.login-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #8B0000, #D4AF37);
  height: 3px;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 18px;
  font-weight: bold;
  letter-spacing: 2px;
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border: 1px solid #B22222;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: linear-gradient(145deg, #B22222 0%, #8B0000 100%);
  box-shadow: 0 4px 20px rgba(139, 0, 0, 0.5);
  transform: translateY(-2px);
}

.register-btn {
  background: linear-gradient(145deg, #1E3A5F 0%, #0D1F33 100%);
  border: 1px solid #2A4A6F;
}

.register-btn:hover {
  background: linear-gradient(145deg, #2A4A6F 0%, #1E3A5F 100%);
  box-shadow: 0 4px 20px rgba(30, 58, 95, 0.5);
}

:deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid #3D3D3D;
  box-shadow: none;
  border-radius: 8px;
}

:deep(.el-input__wrapper:hover) {
  border-color: #8B7355;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #D4AF37;
  box-shadow: 0 0 12px rgba(212, 175, 55, 0.2);
}

:deep(.el-input__inner) {
  color: #F5DEB3;
  height: 40px;
}

:deep(.el-input__inner::placeholder) {
  color: #666;
}

.footer-note {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #2D2D2D;
}

.footer-note p {
  color: #666;
  font-size: 12px;
  margin: 0;
  letter-spacing: 1px;
}
</style>
