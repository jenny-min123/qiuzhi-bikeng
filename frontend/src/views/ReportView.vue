<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import RiskHighlight from '../components/RiskHighlight.vue'
import CompanyCard from '../components/CompanyCard.vue'
import ConsistencyCard from '../components/ConsistencyCard.vue'
import ReportPanel from '../components/ReportPanel.vue'
import { useAnalysisStore } from '../store/analysis'

const route = useRoute()
const store = useAnalysisStore()
const report = computed(() => store.report)

onMounted(async () => {
  const id = route.params.id
  if (id && (!report.value || report.value.report_id !== id)) {
    await store.loadReport(id)
  }
})
</script>

<template>
  <div class="page">
    <el-alert
      v-if="store.error"
      type="error"
      :title="store.error"
      :closable="false"
      show-icon
    />

    <el-empty
      v-if="!report && !store.error"
      description="还没有报告。先去核验一条 JD 吧。"
    >
      <RouterLink to="/analyze">
        <el-button type="primary">开始核验</el-button>
      </RouterLink>
    </el-empty>

    <template v-if="report">
      <RiskHighlight :text="report.jd.text" :hits="report.jd_risk.hits" />
      <CompanyCard :score="report.company_score" />
      <ConsistencyCard :consistency="report.consistency" />
      <ReportPanel :report="report" />
    </template>
  </div>
</template>
