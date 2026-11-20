<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  hits: { type: Array, default: () => [] }
})

const TYPE_CLASS = {
  零门槛类: 'hl-zero',
  高薪异常类: 'hl-salary',
  面试即入类: 'hl-entry',
  能力打压类: 'hl-pressure',
  培训诱导类: 'hl-training',
  收费诱导类: 'hl-fee',
  贷款诱导类: 'hl-loan'
}

function typeClass(type) {
  return TYPE_CLASS[type] || 'hl-other'
}

const parts = computed(() => {
  const sorted = [...props.hits]
    .filter((hit) => Array.isArray(hit.span) && hit.span.length === 2)
    .sort((a, b) => a.span[0] - b.span[0])

  const output = []
  let cursor = 0

  for (const hit of sorted) {
    const [start, end] = hit.span
    if (start < cursor || start >= props.text.length) continue
    if (start > cursor) {
      output.push({ text: props.text.slice(cursor, start) })
    }
    output.push({ text: props.text.slice(start, end), hit })
    cursor = Math.min(end, props.text.length)
  }

  if (cursor < props.text.length) {
    output.push({ text: props.text.slice(cursor) })
  }
  return output
})
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2>JD 原文证据</h2>
      <span class="muted">命中 {{ hits.length }} 处风险话术</span>
    </div>

    <p v-if="!hits.length" class="empty">
      规则引擎未命中风险话术。未命中不代表无风险，请结合公司核验结果与人工判断。
    </p>

    <template v-else>
      <div class="jd-text">
        <template v-for="(part, index) in parts" :key="index">
          <mark
            v-if="part.hit"
            :class="['hl', typeClass(part.hit.type)]"
            :title="part.hit.explanation"
          >
            {{ part.text }}
          </mark>
          <span v-else>{{ part.text }}</span>
        </template>
      </div>

      <ul class="hit-list">
        <li v-for="hit in hits" :key="hit.evidence_id">
          <div>
            <span class="tag">{{ hit.type }}</span>
            <strong>{{ hit.fragment }}</strong>
            <span class="muted">−{{ hit.penalty }} 分</span>
          </div>
          <p class="muted">{{ hit.explanation }}</p>
        </li>
      </ul>
    </template>
  </section>
</template>
