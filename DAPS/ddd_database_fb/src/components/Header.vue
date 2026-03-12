<template>
  <!-- 顶部用户信息栏组件 -->
  <div class="header">
    <div class="header-left">
      <span class="system-name">{{ appName }}</span>
    </div>

    <div class="user-info">
      <span>{{ userInfo.username || 'user_info' }}</span>
      <el-button type="text" @click="logout" style="margin-left: 15px; color: #666;">
        退出
      </el-button>
    </div>
  </div>
</template>

<script>
import { useUserStore } from '@/store'

export default {
  name: 'Header',
  setup() {
    const userStore = useUserStore()
    const appName = import.meta.env.VITE_APP_NAME || '血糖监控系统'

    const logout = () => {
      userStore.logout()
      // 跳转到登录页
      window.location.href = '/login'
    }

    return {
      userInfo: userStore.userInfo,
      logout,
      appName
    }
  }
}
</script>

<style scoped>
/* 头部：左侧显示系统名称，右侧显示用户信息 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
}

.header-left .system-name {
  font-size: 35px;
  font-weight: 600;
  color: #2c3e50;
}

.user-info {
  display: flex;
  align-items: center;
}
</style>