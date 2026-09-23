<template>
  <div class="app-shell">
    <h1>CropDP-KG</h1>
    <p>本地前端已启动成功。</p>
    <div class="card">
      <h2>项目状态</h2>
      <ul>
        <li>Django 后端：已运行</li>
        <li>Vue 前端：已补齐入口</li>
        <li>数据平台：可继续扩展</li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style scoped>
.app-shell {
  font-family: Arial, sans-serif;
  max-width: 820px;
  margin: 60px auto;
  padding: 24px;
  color: #1f2937;
}

h1 {
  margin-bottom: 10px;
  color: #0f172a;
}

.card {
  margin-top: 24px;
  padding: 20px 24px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f8fafc;
}

ul {
  margin: 12px 0 0 20px;
  line-height: 1.8;
}
</style>
