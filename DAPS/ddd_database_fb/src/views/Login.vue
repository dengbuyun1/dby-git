<template>
  <!-- 登录页面 -->
  <div class="login-container">
    <div class="login-box">
      <!-- 登录表单标题 -->
      <h2 class="login-title">{{ isLogin ? '登录' : '注册' }}</h2>

      <!-- 登录/注册表单 -->
      <el-form ref="loginForm" :model="loginData" :rules="loginRules" label-position="top" class="login-form">
        <!-- 用户名输入框 -->
        <el-form-item label="用户名" prop="username">
          <el-input v-model="loginData.username" placeholder="请输入用户名" size="large" />
        </el-form-item>

        <!-- 邮箱输入框（仅注册时显示） -->
        <el-form-item v-if="!isLogin" label="邮箱" prop="email">
          <el-input v-model="loginData.email" placeholder="请输入邮箱" size="large" />
        </el-form-item>

        <!-- 密码输入框 -->
        <el-form-item label="密码" prop="password">
          <el-input v-model="loginData.password" type="password" placeholder="请输入密码" size="large" show-password />
        </el-form-item>

        <!-- 确认密码输入框（仅注册时显示） -->
        <el-form-item v-if="!isLogin" label="确认密码" prop="confirmPassword">
          <el-input v-model="loginData.confirmPassword" type="password" placeholder="请再次输入密码" size="large"
            show-password />
        </el-form-item>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" @click="handleSubmit" :loading="loading">
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 切换登录/注册模式 -->
      <div class="switch-mode">
        <span>{{ isLogin ? '还没有账号？' : '已有账号？' }}</span>
        <el-button type="text" @click="switchMode">
          {{ isLogin ? '立即注册' : '立即登录' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store'
import { authAPI } from '@/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const userStore = useUserStore()

    // 响应式数据
    const isLogin = ref(true) // 是否为登录模式
    const loading = ref(false) // 加载状态
    const loginForm = ref(null) // 表单引用

    // 表单数据
    const loginData = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    })

    // 表单验证规则
    const loginRules = reactive({
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请确认密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== loginData.password) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          },
          trigger: 'blur'
        }
      ]
    })

    // 切换登录/注册模式
    const switchMode = () => {
      isLogin.value = !isLogin.value
      // 重置表单
      loginForm.value?.resetFields()
      Object.keys(loginData).forEach(key => {
        loginData[key] = ''
      })
    }

    // 处理表单提交
    const handleSubmit = async () => {
      try {
        // 表单验证
        await loginForm.value.validate()

        loading.value = true

        if (isLogin.value) {
          // 登录逻辑
          await handleLogin()
        } else {
          // 注册逻辑
          await handleRegister()
        }
      } catch (error) {
        console.error('表单验证失败:', error)
      } finally {
        loading.value = false
      }
    }

    // 登录处理
    const handleLogin = async () => {
      try {
        const response = await authAPI.login({
          username: loginData.username,
          password: loginData.password
        })

        // 存储用户信息
        userStore.login(response.data)

        ElMessage.success('登录成功！')
        // 跳转到选择页面
        router.push('/choose')
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '登录失败，请检查用户名和密码')
      }
    }

    // 注册处理
    const handleRegister = async () => {
      try {
        const response = await authAPI.register({
          username: loginData.username,
          email: loginData.email,
          password: loginData.password
        })

        ElMessage.success('注册成功！请登录')
        // 切换到登录模式
        switchMode()
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '注册失败，请重试')
      }
    }

    return {
      isLogin,
      loading,
      loginForm,
      loginData,
      loginRules,
      switchMode,
      handleSubmit
    }
  }
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2%;
  box-sizing: border-box;
}

.login-box {
  width: 100%;
  max-width: 400px;
  padding: 3%;
  background: white;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  box-sizing: border-box;
}

.login-title {
  text-align: center;
  margin-bottom: 8%;
  color: #333;
  font-size: 1.8em;
  font-weight: bold;
}

.login-form {
  margin-bottom: 5%;
}

.switch-mode {
  text-align: center;
  color: #666;
  font-size: 0.9em;
}

.switch-mode span {
  margin-right: 5px;
}

/* 响应式断点 */
@media (max-width: 1400px) {
  .login-box {
    max-width: 380px;
    padding: 2.5%;
  }

  .login-title {
    font-size: 1.7em;
  }
}

@media (max-width: 1200px) {
  .login-box {
    max-width: 360px;
    padding: 2%;
  }

  .login-title {
    font-size: 1.6em;
  }
}

@media (max-width: 768px) {
  .login-box {
    max-width: 90%;
    padding: 6%;
  }

  .login-title {
    font-size: 1.5em;
    margin-bottom: 6%;
  }
}

@media (max-width: 480px) {
  .login-box {
    max-width: 95%;
    padding: 8%;
  }

  .login-title {
    font-size: 1.4em;
  }
}
</style>