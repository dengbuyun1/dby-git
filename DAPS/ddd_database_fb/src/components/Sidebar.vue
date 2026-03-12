<template>
  <!-- 侧边栏组件 - 左侧导航栏 -->
  <div class="sidebar">
    <!-- 顶部Logo和名称区域 -->
    <div class="logo-section">
      <router-link to="/" class="logo-link" aria-label="Home">
        <div class="logo-mark" aria-hidden="true">
          <!-- 优先显示 public 根目录下的 logo 图片（例如 public/logo.png），不存在时显示下面的 SVG 备选 -->
          <img src="/logo.png" alt="logo" class="logo-img" onerror="this.style.display='none'" />

          <!-- 简洁医护风格 SVG 标志（作为后备） -->
          <svg viewBox="0 0 64 64" width="36" height="36" xmlns="http://www.w3.org/2000/svg" focusable="false">
            <defs>
              <linearGradient id="g1" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0" stop-color="#4f83f8" />
                <stop offset="1" stop-color="#6ad3ff" />
              </linearGradient>
            </defs>
            <circle cx="32" cy="32" r="30" fill="url(#g1)" />
            <rect x="28" y="16" width="8" height="32" rx="2" fill="#fff" />
            <rect x="16" y="28" width="32" height="8" rx="2" fill="#fff" />
          </svg>
        </div>

        <div class="logo-text">
          <span class="app-name">DAPS</span>
          <small class="app-sub">Patient Monitor</small>
        </div>
      </router-link>
    </div>

    <!-- 导航菜单区域 -->
    <div class="nav-menu">
      <!-- 添加患者按钮 -->
      <div class="nav-item" :class="{ active: currentRoute === 'choose' }" @click="navigateTo('choose')">
        添加患者
      </div>

      <!-- 查看虚拟患者按钮 -->
      <div class="nav-item" :class="{ active: currentRoute === 'v_patients' }"
        @click="navigateTo('v-patients-monitor')">
        虚拟患者监控
      </div>

      <!-- 测试仿真按钮
      <div class="nav-item"
        :class="{ active: currentRoute === 'test_simulation' || $route.path === '/test-simulation' }"
        @click="navigateToSimulation">
        测试仿真
      </div> -->

      <!-- 查看真实患者按钮 -->
      <div class="nav-item" :class="{ active: currentRoute === 'true_patients' }"
        @click="navigateTo('true-patients-monitor')">
        真实患者监控
      </div>

      <!-- 患者信息管理按钮
      <div class="nav-item" :class="{ active: currentRoute === 'patients_info' }" @click="navigateTo('patients-list')">
        患者信息管理
      </div> -->

      <!-- 数字孪生匹配按钮(新增) -->
      <div class="nav-item" :class="{ active: currentRoute === 'digital_twin' }" @click="navigateTo('digital-twin')">
        数字孪生匹配
      </div>

      <!-- 数据管理按钮(新增) -->
      <div class="nav-item" :class="{ active: currentRoute === 'simulations_list' }"
        @click="navigateTo('simulations-list')">
        数据管理
      </div>


    </div>

    <!-- 底部设置区域 -->
    <div class="settings-section" @click="openSettings">
      setting
    </div>
  </div>
</template>

<script>
export default {
  name: 'Sidebar',
  props: {
    // 当前激活的路由
    currentRoute: {
      type: String,
      default: ''
    }
  },
  methods: {
    // 导航到指定页面
    navigateTo(routeName) {
      this.$emit('navigate', routeName)
      this.$router.push(`/${routeName}`)
    },

    // 导航到测试仿真界面
    navigateToSimulation() {
      this.$emit('navigate', 'test-simulation')
      this.$router.push('/test-simulation')
    },

    // 打开设置
    openSettings() {
      this.$emit('open-settings')
      // 这里可以添加设置页面的逻辑
      console.log('打开设置页面')
    }
  }
}
</script>

<style scoped>
/* 侧边栏样式已在全局样式中定义 */

.logo-section {
  padding: 12px 14px;
  display: flex;
  align-items: center;
  height: 64px;
  /* 保持高度一致 */
}

.logo-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
}

.logo-mark {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 40px;
  border-radius: 8px;
  overflow: hidden;
}

.logo-img {
  width: 40px;
  height: 40px;
  object-fit: cover;
  display: block;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.app-name {
  font-weight: 700;
  color: #ffffff;
  /* 在深色侧栏上更醒目 */
  font-size: 14px;
}

.app-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
}

/* 悬停/聚焦效果（增强可点击感） */
.logo-link:hover .logo-mark,
.logo-link:focus .logo-mark {
  transform: translateY(-2px);
  transition: transform 120ms ease;
}

/* 如果侧边栏背景较浅，调整文字颜色（若你有全局主题开关，可用类控制） */
.sidebar.light .app-name,
.sidebar.light .app-sub {
  color: #24324a;
}
</style>