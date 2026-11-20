<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Object, required: true }
})

const levelText = {
  low_risk: '低风险',
  medium_risk: '中风险',
  high_risk: '高风险',
  unknown: '未评估'
}

const level = computed(() => levelText[props.score.level] || props.score.level)
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2>公司可信度核验</h2>
      <span class="muted">
        证据源 {{ score.available ? '已获取' : '未获取' }}
      </span>
    </div>

    <template v-if="score.available">
      <div class="score-row">
        <div class="score-value">
          <template v-if="score.score !== null && score.score !== undefined">
            {{ score.score }}<small>/ 100</small>
          </template>
          <template v-else>—</template>
        </div>
        <div class="score-meta">
          <span>{{ level }}</span>
          <span>置信度：{{ score.confidence }}</span>
          <span v-if="score.coverage != null">
            证据覆盖：{{ Math.round(score.coverage * 100) }}%
          </span>
        </div>
      </div>

      <p v-if="score.score === null || score.score === undefined" class="empty">
        可用证据覆盖不足，暂不给出可信度分数。以下仅列出已获取到的风险项。
      </p>

      <p v-else-if="!score.deductions.length" class="empty">
        当前证据未发现低于基线的事项。
      </p>

      <ul v-else class="deductions">
        <li v-for="item in score.deductions" :key="item.evidence_id + item.source">
          <strong>{{ item.source }}</strong>
          <span>：{{ item.fact }}</span>
          <span class="muted"> — {{ item.explanation }}</span>
        </li>
      </ul>
    </template>

    <p v-else class="empty">
      本次未获取到任何主体证据，因此不给出公司可信度分数。
      缺失来源：{{ score.missing_sources.join('、') || '未提供公司名称' }}。
    </p>

    <p v-if="score.missing_sources.length && score.available" class="rule-note">
      缺失信号：{{ score.missing_sources.join('、') }}。评分已按可用证据重新归一化，置信度相应降级。
    </p>
  </section>
</template>
