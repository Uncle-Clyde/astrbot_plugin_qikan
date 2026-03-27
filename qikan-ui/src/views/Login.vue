<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="title">⚔️ 骑砍英雄传</h1>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.name" placeholder="角色名" maxlength="12" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" show-password />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.adminKey" type="password" placeholder="访问密码（管理员设置）" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleLogin" style="width: 100%">
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="registerForm.name" placeholder="角色名" maxlength="12" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.password" type="password" placeholder="密码" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleRegister" style="width: 100%">
                注 册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
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
const registerForm = reactive({ name: '', password: '' })

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
  await gameStore.register(registerForm.name, registerForm.password)
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
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-box {
  width: 360px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.title {
  text-align: center;
  color: #ffd700;
  margin-bottom: 30px;
  font-size: 28px;
}
</style>
