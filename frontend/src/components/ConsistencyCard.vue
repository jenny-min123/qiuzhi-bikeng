<script setup>
import { computed } from 'vue'

const props = defineProps({
  consistency: { type: Object, required: true }
})

const severityText = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '极高'
}

const mismatches = computed(() => props.consistency.mismatches || [])
const criticalCount = computed(() => (props.consistency.critical || []).length)
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2>JD—主体一致性校验</h2>
      <span class="muted">
        不一致 {{ mismatches.length }} 项
        <template v-if="criticalCount">· 一票否决 {{ criticalCount }} 项</template>
      </span>
    </div>

    <p v-if="!mismatches.length" class="empty">
      本次没有发现「JD 宣称」与「主体事实」的直接矛盾。
      这可能是双方确实一致，也可能是相应证据未获取，请查看下方未核对项。
    </p>

    <div v-else class="compare-list">
      <div v-for="item in mismatches" :key="item.evidence_id" class="compare-row">
        <span class="compare-category">{{ item.category }}</span>
        <span>JD：{{ item.jd_claim || '—' }}</span>
        <span class="compare-fact">事实：{{ item.subject_fact }}</span>
        <span :class="['severity', `severity-${item.severity}`]">
          {{ severityText[item.severity] || item.severity }}
        </span>
      </div>
    </div>

    <p class="rule-note">
      已核对：{{ consistency.rules_evaluated.join('、') || '无' }}。
      证据不足暂未核对：{{ consistency.rules_not_evaluable.join('、') || '无' }}。
      未核对不代表无风险。
    </p>
  </section>
</template>
