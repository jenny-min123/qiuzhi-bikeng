<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import JdInput from '../components/JdInput.vue'
import RiskHighlight from '../components/RiskHighlight.vue'
import CompanyCard from '../components/CompanyCard.vue'
import ConsistencyCard from '../components/ConsistencyCard.vue'
import ReportPanel from '../components/ReportPanel.vue'
import { useAnalysisStore } from '../store/analysis'

const store = useAnalysisStore()
const route = useRoute()
const router = useRouter()
const report = computed(() => store.report)
const initialCompany = computed(() => String(route.query.company || ''))

async function handleSubmit({ jdText, companyName }) {
  await store.run(jdText, companyName)
  if (store.report) {
    router.push({ name: 'report', params: { id: store.report.report_id } })
  }
}
</script>

<template>
  <div class="page">
    <JdInput
      :loading="store.loading"
      :initial-company="initialCompany"
      @submit="handleSubmit"
    />

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
      <p v-if="!report.company_score.available" class="rule-note">
        该公司暂无主体证据，可以
        <RouterLink to="/snapshot">上传工商页面截图补充 →</RouterLink>
      </p>
      <ConsistencyCard :consistency="report.consistency" />
      <ReportPanel :report="report" />
    </template>
  </div>
</template>
