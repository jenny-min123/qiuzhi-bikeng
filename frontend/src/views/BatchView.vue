<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { runBatch } from '../api'

const input = ref('')
const loading = ref(false)
const result = ref(null)

const items = computed(() => result.value?.items ?? [])
const distribution = computed(() => result.value?.risk_distribution ?? {})
const categories = computed(() => result.value?.risk_categories ?? {})

const levelText = {
  high: '高危',
  medium: '中风险',
  low: '低风险'
}

const suggestionType = {
  建议放弃: 'danger',
  谨慎投递: 'warning',
  建议投递: 'success'
}

async function submit() {
  const jdList = input.value
    .split(/\n\s*\n/)
    .map((item) => item.trim())
    .filter(Boolean)

  if (!jdList.length) {
    ElMessage.warning('请先粘贴 JD，多条之间用空行分隔')
    return
  }
  if (jdList.length > 30) {
    ElMessage.warning('单次最多 30 条，已截取前 30 条')
  }

  loading.value = true
  try {
    result.value = await runBatch({ jd_list: jdList.slice(0, 30) })
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.detail || error?.message || '批量分析失败'
    )
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <section class="card">
      <div class="card-head">
        <h2>批量模式</h2>
        <span class="muted">一次粘贴 1~30 条 JD，用空行分隔</span>
      </div>
      <el-input
        v-model="input"
        type="textarea"
        :rows="12"
        resize="vertical"
        placeholder="第一条 JD……&#10;&#10;第二条 JD……"
      />
      <div class="input-actions">
        <el-button type="primary" :loading="loading" @click="submit">
          批量核验
        </el-button>
        <span class="muted">当前仅基于规则引擎输出岗位侧风险，主体核验需单条分析。</span>
      </div>
    </section>

    <template v-if="result">
      <section class="card">
        <div class="card-head">
          <h3>风险分布</h3>
          <span class="muted">共 {{ items.length }} 条</span>
        </div>
        <div class="batch-summary">
          <div class="report-stat">
            <div class="stat-label">高危</div>
            <div class="stat-value">{{ distribution.high ?? 0 }}</div>
          </div>
          <div class="report-stat">
            <div class="stat-label">中风险</div>
            <div class="stat-value">{{ distribution.medium ?? 0 }}</div>
          </div>
          <div class="report-stat">
            <div class="stat-label">低风险</div>
            <div class="stat-value">{{ distribution.low ?? 0 }}</div>
          </div>
        </div>
        <p v-if="Object.keys(categories).length" class="rule-note">
          命中类别：
          <el-tag
            v-for="(count, type) in categories"
            :key="type"
            class="tag"
            effect="plain"
          >
            {{ type }} {{ count }}
          </el-tag>
        </p>
      </section>

      <section class="card">
        <div class="card-head">
          <h3>逐条结果</h3>
        </div>
        <el-table :data="items" size="small" stripe>
          <el-table-column prop="jd_index" label="#" width="60" />
          <el-table-column prop="score" label="风险分" width="90" />
          <el-table-column label="等级" width="100">
            <template #default="{ row }">
              {{ levelText[row.level] || row.level }}
            </template>
          </el-table-column>
          <el-table-column label="建议">
            <template #default="{ row }">
              <el-tag :type="suggestionType[row.suggestion] || 'info'" effect="plain">
                {{ row.suggestion }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </div>
</template>
