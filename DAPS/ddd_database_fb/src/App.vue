<template>
  <div id="app">
    <!-- 路由视图 - 所有页面都将在这里显示 -->
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>