<template>
  <div class="cropdp-container">
    <!-- 顶部状态导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <div class="logo-icon">🌿</div>
        <div>
          <h1 class="header-title">CropDP-KG 农作物病虫害知识图谱平台</h1>
          <p class="header-sub">基于知识图谱与拓扑推理的农作物病虫害智能分析工作台</p>
        </div>
      </div>
      <div class="header-stats" v-if="stats">
        <div class="stat-badge">
          <span class="stat-num">{{ stats.total_nodes.toLocaleString() }}</span>
          <span class="stat-label">实体节点</span>
        </div>
        <div class="stat-badge highlight">
          <span class="stat-num">{{ stats.total_relationships.toLocaleString() }}</span>
          <span class="stat-label">关联关系</span>
        </div>
        <div class="stat-badge">
          <span class="stat-num">8</span>
          <span class="stat-label">本体类目</span>
        </div>
      </div>
    </header>

    <!-- 主工作区 -->
    <main class="main-workspace">
      <!-- 左侧：图谱可视化画布与控制面板 -->
      <section class="graph-section">
        <!-- 工具操作栏 -->
        <div class="graph-toolbar">
          <div class="search-box">
            <input
              type="text"
              v-model="searchKeyword"
              placeholder="搜索病虫害、作物、症状 (如: 桃炭疽病、草莓、穿孔)..."
              @keyup.enter="handleSearch"
            />
            <button class="btn btn-primary" @click="handleSearch">
              <span>🔍 检索子图</span>
            </button>
          </div>
          <div class="quick-tags">
            <span class="tag-title">热点实体:</span>
            <span
              v-for="item in hotEntities"
              :key="item"
              class="quick-tag"
              @click="loadSubgraph(item)"
            >
              {{ item }}
            </span>
          </div>
        </div>

        <!-- ECharts 力导向图容器 -->
        <div class="chart-wrapper">
          <div ref="chartContainer" class="echarts-container"></div>
          <div class="chart-legend">
            <span class="legend-item" v-for="(cat, idx) in categories" :key="cat.name">
              <span class="legend-dot" :style="{ backgroundColor: categoryColors[idx] }"></span>
              {{ cat.name }} ({{ categoryZh[cat.name] || cat.name }})
            </span>
          </div>
          <div class="chart-overlay-tip" v-if="loadingGraph">
            <div class="spinner"></div>
            <span>正在进行图谱子图推理与渲染...</span>
          </div>
        </div>
      </section>

      <!-- 右侧：智能诊断与节点检查侧边栏 -->
      <aside class="sidebar-section">
        <!-- 侧边栏 Tab 切换 -->
        <div class="tab-header">
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'diagnose' }"
            @click="currentTab = 'diagnose'"
          >
            🩺 智能辅助诊断
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'inspector' }"
            @click="currentTab = 'inspector'"
          >
            🔬 实体属性探查
          </button>
        </div>

        <!-- 诊断推理面板 -->
        <div class="tab-body" v-show="currentTab === 'diagnose'">
          <div class="form-card">
            <h3>农作物病害图推理诊断</h3>
            <p class="form-desc">输入农作物受害特征，基于图谱路径多跳匹配与拓扑交集计算候选病害。</p>

            <div class="form-item">
              <label>寄主作物 <span class="required">*</span></label>
              <input
                type="text"
                v-model="diagForm.crop"
                placeholder="例如: 桃树、草莓、苹果、香蕉"
              />
              <div class="mini-tags">
                <span v-for="c in quickCrops" :key="c" @click="diagForm.crop = c">{{ c }}</span>
              </div>
            </div>

            <div class="form-item">
              <label>受害部位 (可选)</label>
              <select v-model="diagForm.part">
                <option value="">-- 全部受害部位 --</option>
                <option v-for="p in commonParts" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>

            <div class="form-item">
              <label>观察到的典型症状关键词</label>
              <input
                type="text"
                v-model="diagForm.symptoms"
                placeholder="多个以逗号隔开 (如: 水渍状, 凹陷, 红褐色)"
              />
              <div class="mini-tags">
                <span
                  v-for="s in quickSymptoms"
                  :key="s"
                  @click="appendSymptom(s)"
                >
                  +{{ s }}
                </span>
              </div>
            </div>

            <button class="btn btn-action" :disabled="diagLoading" @click="executeDiagnosis">
              <span v-if="!diagLoading">🚀 执行图谱智能研判</span>
              <span v-else>正在推理计算中...</span>
            </button>
          </div>

          <!-- 诊断结果展示 -->
          <div class="result-list" v-if="diagResults && diagResults.length">
            <h4 class="result-title">研判候选病害列表 (Top {{ diagResults.length }})</h4>
            <div
              v-for="(item, idx) in diagResults"
              :key="item.name"
              class="result-card"
              :class="{ top1: idx === 0 }"
              @click="loadSubgraph(item.name)"
            >
              <div class="res-head">
                <div class="res-name-box">
                  <span class="rank-badge">{{ idx + 1 }}</span>
                  <span class="res-name">{{ item.name }}</span>
                  <span class="type-tag" :class="item.type.toLowerCase()">{{ item.type }}</span>
                </div>
                <div class="res-score">
                  <span class="score-val">{{ item.confidence_score }}%</span>
                  <span class="score-label">置信度</span>
                </div>
              </div>

              <div class="score-progress">
                <div class="score-bar" :style="{ width: item.confidence_score + '%' }"></div>
              </div>

              <div class="res-detail-row">
                <span class="detail-label">拉丁学名:</span>
                <span class="detail-val italic">{{ item.latin_name }}</span>
              </div>

              <div class="res-detail-row" v-if="item.matched_symptoms && item.matched_symptoms.length">
                <span class="detail-label">命中特征:</span>
                <span class="detail-val match-highlight">
                  {{ item.matched_symptoms.join('、') }}
                </span>
              </div>

              <div class="res-detail-row" v-if="item.conditions && item.conditions.length">
                <span class="detail-label">诱发环境:</span>
                <span class="detail-val text-muted">
                  {{ item.conditions.join('、') }}
                </span>
              </div>

              <div class="card-action">
                <span>点击在左侧展开完整知识子图 ➔</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 节点检查器面板 -->
        <div class="tab-body" v-show="currentTab === 'inspector'">
          <div class="inspector-card" v-if="selectedNode">
            <div class="node-badge" :style="{ backgroundColor: getNodeColor(selectedNode.category) }">
              {{ selectedNode.type || categories[selectedNode.category].name }}
            </div>
            <h2 class="node-title">{{ selectedNode.name }}</h2>

            <div class="prop-group" v-if="selectedNode.latin_name">
              <span class="prop-name">拉丁学术双名:</span>
              <span class="prop-value italic">{{ selectedNode.latin_name }}</span>
            </div>

            <div class="prop-group" v-if="selectedNode.english_name">
              <span class="prop-name">英文名称:</span>
              <span class="prop-value">{{ selectedNode.english_name }}</span>
            </div>

            <div class="prop-group">
              <span class="prop-name">本体类型:</span>
              <span class="prop-value">{{ selectedNode.type }}</span>
            </div>

            <div class="prop-group">
              <span class="prop-name">当前子图相连实体数:</span>
              <span class="prop-value">{{ getConnectedCount(selectedNode.id) }} 个关联</span>
            </div>

            <div class="inspector-actions">
              <button class="btn btn-primary" @click="loadSubgraph(selectedNode.name)">
                🔄 置为中心展开
              </button>
            </div>
          </div>

          <div class="inspector-empty" v-else>
            <div class="empty-icon">👆</div>
            <p>请点击左侧画布上的任意节点，查看其学术属性、为害特征与多跳关联。</p>
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'App',
  data() {
    return {
      stats: null,
      searchKeyword: '桃炭疽病',
      currentTab: 'diagnose',
      loadingGraph: false,
      diagLoading: false,
      chartInstance: null,
      selectedNode: null,
      currentGraphData: { nodes: [], links: [] },

      hotEntities: ['桃炭疽病', '草莓枯萎病', '香蕉黑带象甲', '桃细菌性穿孔病', '斜纹夜蛾', '水稻'],
      quickCrops: ['桃树', '草莓', '香蕉', '苹果', '水稻', '大豆'],
      commonParts: ['果实', '叶片', '枝干', '根系', '花器', '植株'],
      quickSymptoms: ['水渍状', '凹陷', '红褐色', '穿孔', '霉层', '枯萎', '发黄', '轮纹'],

      diagForm: {
        crop: '桃树',
        part: '果实',
        symptoms: '水渍状, 凹陷, 红褐色'
      },
      diagResults: [],

      categoryColors: ['#ef4444', '#f97316', '#10b981', '#8b5cf6', '#3b82f6', '#06b6d4', '#f59e0b', '#ec4899'],
      categories: [
        { name: 'Disease' },
        { name: 'Pest' },
        { name: 'Crop' },
        { name: 'Part' },
        { name: 'Symptom' },
        { name: 'Condition' },
        { name: 'Region' },
        { name: 'Temperature' }
      ],
      categoryZh: {
        Disease: '病害',
        Pest: '害虫',
        Crop: '寄主作物',
        Part: '受害部位',
        Symptom: '症状特征',
        Condition: '发病诱因',
        Region: '主要分布',
        Temperature: '发生温度'
      }
    };
  },
  mounted() {
    this.initChart();
    this.fetchStats();
    this.loadSubgraph('桃炭疽病');
    this.executeDiagnosis();

    window.addEventListener('resize', this.handleResize);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize);
    if (this.chartInstance) {
      this.chartInstance.dispose();
    }
  },
  methods: {
    getApiUrl(path) {
      // 兼容开发模式直接调 Django 8000 端口或反向代理
      return (window.location.port === '8080' ? 'http://127.0.0.1:8000' : '') + path;
    },

    async fetchStats() {
      try {
        const res = await fetch(this.getApiUrl('/api/graph/stats/'));
        const json = await res.json();
        if (json.code === 200) {
          this.stats = json.data;
        }
      } catch (e) {
        console.error('获取统计失败', e);
      }
    },

    initChart() {
      const container = this.$refs.chartContainer;
      if (!container) return;

      this.chartInstance = echarts.init(container);
      this.chartInstance.on('click', (params) => {
        if (params.dataType === 'node') {
          this.selectedNode = params.data;
          this.currentTab = 'inspector';
        }
      });
    },

    handleResize() {
      if (this.chartInstance) {
        this.chartInstance.resize();
      }
    },

    async loadSubgraph(name) {
      if (!name) return;
      this.loadingGraph = true;
      try {
        const url = this.getApiUrl(`/api/graph/subgraph/?name=${encodeURIComponent(name)}&limit=60`);
        const res = await fetch(url);
        const json = await res.json();
        if (json.code === 200) {
          this.currentGraphData = json.data;
          this.renderGraph(json.data);
          // 默认选中中心节点
          this.selectedNode = json.data.nodes[0];
        } else {
          alert(json.message || '未查询到相关子图');
        }
      } catch (e) {
        console.error('加载子图失败', e);
      } finally {
        this.loadingGraph = false;
      }
    },

    renderGraph(data) {
      if (!this.chartInstance) return;

      // 调整节点颜色与样式
      const nodes = data.nodes.map((n) => {
        const catIdx = n.category !== undefined ? n.category : 0;
        return {
          ...n,
          itemStyle: {
            color: this.categoryColors[catIdx] || '#3b82f6',
            borderColor: '#ffffff',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(0,0,0,0.15)'
          }
        };
      });

      const option = {
        tooltip: {
          formatter: (params) => {
            if (params.dataType === 'node') {
              const d = params.data;
              return `<div style="font-weight:bold;margin-bottom:4px;">${d.name} (${d.type})</div>
                      ${d.latin_name ? `<div>学名: <i>${d.latin_name}</i></div>` : ''}
                      ${d.english_name ? `<div>英文: ${d.english_name}</div>` : ''}`;
            }
            if (params.dataType === 'edge') {
              return `${params.data.source} ➔ <b>${params.data.value}</b> ➔ ${params.data.target}`;
            }
          }
        },
        animationDurationUpdate: 1200,
        animationEasingUpdate: 'quinticInOut',
        series: [
          {
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: data.links,
            categories: this.categories,
            roam: true,
            label: {
              show: true,
              position: 'right',
              formatter: '{b}',
              fontSize: 11,
              color: '#1f2937'
            },
            edgeLabel: {
              show: true,
              formatter: (x) => x.data.value || '',
              fontSize: 9,
              color: '#6b7280'
            },
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: [4, 8],
            lineStyle: {
              color: 'source',
              width: 1.5,
              opacity: 0.75
            },
            force: {
              repulsion: 380,
              edgeLength: [60, 140],
              gravity: 0.12
            },
            emphasis: {
              focus: 'adjacency',
              lineStyle: {
                width: 3
              }
            }
          }
        ]
      };

      this.chartInstance.setOption(option, true);
    },

    handleSearch() {
      if (this.searchKeyword.trim()) {
        this.loadSubgraph(this.searchKeyword.trim());
      }
    },

    appendSymptom(s) {
      if (!this.diagForm.symptoms) {
        this.diagForm.symptoms = s;
      } else {
        const arr = this.diagForm.symptoms.split(/[,，]/).map((x) => x.trim());
        if (!arr.includes(s)) {
          this.diagForm.symptoms += ', ' + s;
        }
      }
    },

    async executeDiagnosis() {
      if (!this.diagForm.crop.trim()) {
        alert('请输入寄主作物名称');
        return;
      }

      this.diagLoading = true;
      try {
        const url = this.getApiUrl('/api/graph/diagnose/');
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            crop: this.diagForm.crop.trim(),
            part: this.diagForm.part.trim() || undefined,
            symptoms: this.diagForm.symptoms.trim()
          })
        });
        const json = await res.json();
        if (json.code === 200) {
          this.diagResults = json.data.candidates;
        }
      } catch (e) {
        console.error('诊断失败', e);
      } finally {
        this.diagLoading = false;
      }
    },

    getNodeColor(catIdx) {
      return this.categoryColors[catIdx] || '#3b82f6';
    },

    getConnectedCount(nodeId) {
      if (!this.currentGraphData || !this.currentGraphData.links) return 0;
      return this.currentGraphData.links.filter(
        (l) => l.source === nodeId || l.target === nodeId
      ).length;
    }
  }
};
</script>

<style scoped>
/* 调色板与全局布局 */
.cropdp-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  color: #1e293b;
  overflow: hidden;
}

/* 顶部导航 */
.app-header {
  height: 68px;
  background: #0f172a;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
  background: rgba(255, 255, 255, 0.1);
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
}

.header-title {
  font-size: 19px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.5px;
}

.header-sub {
  font-size: 12px;
  color: #94a3b8;
  margin: 2px 0 0 0;
}

.header-stats {
  display: flex;
  gap: 16px;
}

.stat-badge {
  background: rgba(255, 255, 255, 0.08);
  padding: 6px 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-badge.highlight {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.stat-num {
  font-size: 16px;
  font-weight: bold;
  color: #38bdf8;
}

.stat-badge.highlight .stat-num {
  color: #34d399;
}

.stat-label {
  font-size: 11px;
  color: #94a3b8;
}

/* 主工作区 */
.main-workspace {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧图谱区域 */
.graph-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  position: relative;
}

.graph-toolbar {
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.search-box {
  display: flex;
  gap: 8px;
  flex: 1;
  max-width: 480px;
}

.search-box input {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.search-box input:focus {
  border-color: #3b82f6;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.quick-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.tag-title {
  color: #64748b;
}

.quick-tag {
  background: #f1f5f9;
  color: #334155;
  padding: 4px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-tag:hover {
  background: #e2e8f0;
  color: #0284c7;
}

/* 图谱画布 */
.chart-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.echarts-container {
  width: 100%;
  height: 100%;
}

.chart-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(4px);
  padding: 8px 14px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #475569;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.chart-overlay-tip {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(15, 23, 42, 0.85);
  color: #ffffff;
  padding: 12px 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

/* 右侧边栏 */
.sidebar-section {
  width: 440px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e2e8f0;
}

.tab-header {
  display: flex;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
}

.tab-btn {
  flex: 1;
  padding: 14px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
  background: #f8fafc;
}

.tab-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

/* 诊断表单卡片 */
.form-card {
  background: #ffffff;
  padding: 18px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.form-card h3 {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: #0f172a;
}

.form-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 14px 0;
}

.form-item {
  margin-bottom: 12px;
}

.form-item label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}

.required {
  color: #ef4444;
}

.form-item input,
.form-item select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.mini-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.mini-tags span {
  font-size: 11px;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 10px;
  cursor: pointer;
}

.mini-tags span:hover {
  background: #e2e8f0;
  color: #2563eb;
}

.btn-action {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff;
  margin-top: 8px;
}

.btn-action:hover {
  opacity: 0.95;
}

/* 诊断结果 */
.result-list {
  margin-top: 18px;
}

.result-title {
  font-size: 13px;
  color: #475569;
  margin: 0 0 10px 0;
}

.result-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.result-card.top1 {
  border-left: 4px solid #10b981;
  background: #f0fdf4;
}

.res-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.res-name-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-badge {
  background: #e2e8f0;
  color: #334155;
  font-size: 11px;
  font-weight: bold;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.top1 .rank-badge {
  background: #10b981;
  color: #ffffff;
}

.res-name {
  font-size: 14px;
  font-weight: bold;
  color: #0f172a;
}

.type-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #fee2e2;
  color: #b91c1c;
}

.type-tag.pest {
  background: #ffedd5;
  color: #c2410c;
}

.res-score {
  text-align: right;
}

.score-val {
  font-size: 16px;
  font-weight: bold;
  color: #059669;
}

.score-label {
  font-size: 10px;
  color: #64748b;
  display: block;
}

.score-progress {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  margin: 8px 0;
  overflow: hidden;
}

.score-bar {
  height: 100%;
  background: #10b981;
}

.res-detail-row {
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  gap: 6px;
}

.detail-label {
  color: #64748b;
  flex-shrink: 0;
}

.detail-val {
  color: #1e293b;
}

.italic {
  font-style: italic;
  font-family: Georgia, serif;
}

.match-highlight {
  color: #2563eb;
  font-weight: 500;
}

.card-action {
  font-size: 11px;
  color: #3b82f6;
  margin-top: 8px;
  text-align: right;
}

/* 节点属性卡片 */
.inspector-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 20px;
}

.node-badge {
  display: inline-block;
  color: #ffffff;
  font-size: 11px;
  font-weight: bold;
  padding: 3px 10px;
  border-radius: 12px;
  margin-bottom: 8px;
}

.node-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #0f172a;
}

.prop-group {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f1f5f9;
}

.prop-name {
  font-size: 11px;
  color: #64748b;
  display: block;
  margin-bottom: 2px;
}

.prop-value {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}

.inspector-actions {
  margin-top: 20px;
}

.inspector-empty {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
}
</style>
