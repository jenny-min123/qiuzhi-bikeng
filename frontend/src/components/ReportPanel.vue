<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

import { exportReport } from '../api'

const props = defineProps({
  report: { type: Object, required: true }
})

const verdict = computed(() => props.report.verdict || {})
const bannerClass = computed(() => {
  const suggestion = verdict.value.final_suggestion
  if (suggestion === '建议放弃') return 'verdict-reject'
  if (suggestion === '谨慎投递') return 'verdict-caution'
  return 'verdict-accept'
})

const levelText = {
  low: '低',
  medium: '中',
  high: '高'
}

function companyScoreText() {
  return props.report.company_score.available
    ? String(props.report.company_score.score)
    : '—'
}

async function onExport(format) {
  try {
    await exportReport(props.report.report_id, format)
    ElMessage.success('导出完成')
  } catch (error) {
    ElMessage.warning(
      error?.response?.data?.detail || '导出功能尚未接入，可先截图分享报告。'
    )
  }
}
</script>

<template>
  <section class="card">
    <el-alert
      v-if="report.need_clarify"
      type="info"
      :title="report.clarify_question"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <div :class="['verdict-banner', bannerClass]">
      <div>
        <div class="verdict-title">{{ verdict.final_suggestion }}</div>
        <div v-if="verdict.one_vote_veto" class="verdict-reason">
          一票否决：{{ verdict.veto_reason }}
        </div>
      </div>
      <div class="report-actions">
        <el-button size="small" @click="onExport('pdf')">导出 PDF</el-button>
        <el-button size="small" @click="onExport('png')">导出长图</el-button>
      </div>
    </div>

    <div class="report-grid">
      <div class="report-stat">
        <div class="stat-label">岗位风险分</div>
        <div class="stat-value">{{ report.jd_risk.score }}</div>
      </div>
      <div class="report-stat">
        <div class="stat-label">公司可信分</div>
        <div class="stat-value">{{ companyScoreText() }}</div>
      </div>
      <div class="report-stat">
        <div class="stat-label">一致性不一致项</div>
        <div class="stat-value">{{ report.consistency.mismatches.length }}</div>
      </div>
    </div>

    <div class="card-head" style="margin-top: 20px">
      <h3>证据链</h3>
      <span class="muted">{{ report.evidence_chain.length }} 条</span>
    </div>

    <p v-if="!report.evidence_chain.length" class="empty">
      本次没有可展示的证据条目。
    </p>

    <ul v-else class="evidence-list">
      <li v-for="item in report.evidence_chain" :key="item.evidence_id">
        <span class="evidence-id">{{ item.evidence_id }}</span>
        <strong>{{ item.source }}</strong>
        <template v-if="item.detail?.fragment">
          · 原文片段「{{ item.detail.fragment }}」
        </template>
        <template v-else-if="item.detail?.summary">
          · {{ item.detail.summary }}
        </template>
        <a v-if="item.link" :href="item.link" target="_blank" rel="noreferrer">
          查看来源
        </a>
      </li>
    </ul>

    <p class="rule-note">
      岗位判定：
      <template v-if="report.jd_risk.classify_available">
        模型 P(招转培) = {{ (report.jd_risk.classify_prob * 100).toFixed(1) }}%，
      </template>
      <template v-else>模型判定不可用（{{ report.jd_risk.classify_note || '未训练模型' }}），</template>
      风险等级 {{ levelText[report.jd_risk.level] || report.jd_risk.level }}。
    </p>

    <p class="disclaimer">{{ report.disclaimer }}</p>
  </section>
</template>

<style scoped>
.report-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
