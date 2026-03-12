<template>
	<!-- 测试仿真：内嵌 lll/pc_fb/front 前端（可配置 URL） -->
	<div class="main-container">
		<Sidebar :currentRoute="'test_simulation'" @navigate="handleNavigate" @open-settings="handleOpenSettings" />
		<div class="main-content">
			<Header />
			<div class="content">
				<div class="frame-toolbar">
					<div class="left">
						<span class="label">测试仿真前端：</span>
						<a :href="targetUrl" target="_blank">{{ targetUrl }}</a>
					</div>
					<div class="right">
						<button class="btn" @click="reloadFrame">刷新</button>
						<button class="btn" @click="openInNew">新标签打开</button>
					</div>
				</div>
				<div class="frame-container">
					<iframe ref="iframeRef" class="simulation-frame" :src="frameSrc" frameborder="0"
						@load="onFrameLoad"></iframe>
					<div v-if="!loaded && hintVisible" class="frame-hint">
						<div>
							<p>正在尝试加载测试仿真页面…</p>
							<p>如果长时间未显示，请确认 lll/pc_fb/front 已启动（默认 http://localhost:4500）。</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

export default {
	name: 'TestSimulation',
	components: {
		Sidebar,
		Header
	},
	setup() {
		const router = useRouter()
		const targetUrl = import.meta.env.VITE_TEST_SIM_URL || 'http://localhost:4500'
		const refreshKey = ref(Date.now())
		const frameSrc = computed(() => {
			const delim = targetUrl.includes('?') ? '&' : '?'
			return `${targetUrl}${delim}v=${refreshKey.value}`
		})
		const iframeRef = ref(null)
		const loaded = ref(false)
		const hintVisible = ref(false)
		let hintTimer = null

		const handleNavigate = (routeName) => {
			console.log('导航到:', routeName)
		}

		const handleOpenSettings = () => {
			console.log('打开设置')
		}

		const openInNew = () => { window.open(targetUrl, '_blank') }
		const reloadFrame = () => {
			try {
				loaded.value = false
				hintVisible.value = true
				if (iframeRef.value) {
					refreshKey.value = Date.now()
				}
			} catch (e) { /* 忽略 */ }
		}
		const onFrameLoad = () => { loaded.value = true; hintVisible.value = false }

		onMounted(() => {
			hintTimer = setTimeout(() => { if (!loaded.value) hintVisible.value = true }, 800)
		})
		onBeforeUnmount(() => { if (hintTimer) clearTimeout(hintTimer) })

		return {
			handleNavigate,
			handleOpenSettings,
			targetUrl,
			frameSrc,
			iframeRef,
			loaded,
			hintVisible,
			openInNew,
			reloadFrame,
			onFrameLoad
		}
	}
}
</script>

<style scoped>
.frame-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 1%;
	padding: 0.5% 1%;
	flex-wrap: wrap;
	gap: 1%;
}

.frame-toolbar .left {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 0.5%;
}

.frame-toolbar .label {
	color: #666;
	margin-right: 0.5%;
	font-size: 0.95em;
}

.frame-toolbar .right {
	display: flex;
	gap: 1%;
}

.frame-toolbar .btn {
	padding: 0.5% 1.5%;
	border: 1px solid #dcdfe6;
	background: #fff;
	border-radius: 4px;
	cursor: pointer;
	font-size: 0.9em;
	transition: all 0.3s ease;
	white-space: nowrap;
}

.frame-toolbar .btn:hover {
	background: #f5f7fa;
	border-color: #409eff;
	color: #409eff;
}

.frame-container {
	position: relative;
	height: calc(100vh - 180px);
	background: #fafafa;
	border: 1px solid #eaeaea;
	border-radius: 6px;
	overflow: hidden;
	width: 100%;
	box-sizing: border-box;
}

.simulation-frame {
	width: 100%;
	height: 100%;
	display: block;
	background: #fff;
	border: none;
}

.frame-hint {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9) 10px, rgba(245, 245, 245, 0.9) 10px, rgba(245, 245, 245, 0.9) 20px);
	color: #666;
	text-align: center;
	padding: 2%;
	font-size: 0.95em;
}

.frame-hint p {
	margin: 0.5% 0;
}

/* 响应式断点 */
@media (max-width: 1400px) {
	.frame-toolbar .label {
		font-size: 0.9em;
	}

	.frame-toolbar .btn {
		font-size: 0.85em;
	}

	.frame-hint {
		font-size: 0.9em;
	}
}

@media (max-width: 1200px) {
	.frame-toolbar {
		padding: 1%;
		gap: 1.5%;
	}

	.frame-container {
		height: calc(100vh - 200px);
	}
}

@media (max-width: 1024px) {
	.frame-toolbar {
		flex-direction: column;
		align-items: stretch;
	}

	.frame-toolbar .left,
	.frame-toolbar .right {
		width: 100%;
		justify-content: space-between;
	}

	.frame-toolbar .btn {
		padding: 1% 2%;
	}
}

@media (max-width: 768px) {
	.frame-toolbar {
		padding: 2%;
		gap: 2%;
	}

	.frame-toolbar .label {
		font-size: 0.85em;
	}

	.frame-toolbar .btn {
		font-size: 0.8em;
		padding: 1.5% 2.5%;
	}

	.frame-container {
		height: calc(100vh - 220px);
	}

	.frame-hint {
		font-size: 0.85em;
		padding: 4%;
	}
}

@media (max-width: 480px) {
	.frame-toolbar .btn {
		font-size: 0.75em;
	}

	.frame-hint {
		font-size: 0.8em;
	}
}
</style>