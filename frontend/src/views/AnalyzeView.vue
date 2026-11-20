<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import JdInput from '../components/JdInput.vue'
import RiskHighlight from '../components/RiskHighlight.vue'
import CompanyCard from '../components/CompanyCard.vue'
import ConsistencyCard from '../components/ConsistencyCard.vue'
import ReportPanel from '../components/ReportPanel.vue'
import { useAnalysisStore } from '../store/analysis'

const store = useAnalysisStore()
const router = useRouter()
const report = computed(() => store.report)

async function handleSubmit({ jdText, companyName }) {
  await store.run(jdText, companyName)
  if (store.report) {
    router.push({ name: 'report', params: { id: store.report.report_id } })
  }
}
</script>

<template>
  <div class="page">
    <JdInput :loading="store.loading" @submit="handleSubmit" />

    <div v-if="store.loading" class="progress-card">
      <div
        v-for="(message, index) in store.progress"
        :key="index"
        class="progress-line"
      >
        <span class="progress-dot"></span>
        <span>{{ message }}</span>
      </div>
      <p v-if="!store.progress.length" class="muted">正在准备分析…</p>
    </div>

    <el-alert
      v-if="store.error"
      type="error"
      :title="store.error"
      :closable="false"
      show-icon
    />

    <template v-if="report && !store.loading">
      <RiskHighlight :text="report.jd.text" :hits="report.jd_risk.hits" />
      <CompanyCard :score="report.company_score" />
      <ConsistencyCard :consistency="report.consistency" />
      <ReportPanel :report="report" />
    </template>
  </div>
</template>
