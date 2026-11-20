<script setup>
import { computed, onMounted, ref } from 'vue'

import { getPhrases } from '../api'

const data = ref(null)
const loading = ref(true)
const error = ref('')

const maxHits = computed(() => {
  const values = (data.value?.categories || []).map((item) => item.corpus_hits)
  return Math.max(1, ...values)
})

const totalHits = computed(() =>
  (data.value?.categories || []).reduce((sum, item) => sum + item.corpus_hits, 0)
)

const categories = computed(() => data.value?.categories || [])
const meta = computed(() => data.value?.meta || {})
const corpus = computed(() => data.value?.corpus || {})

// 内容依据：V3 2.2 / 4.3 / 6.3 与五部门风险提示；只做信息提示，不替代法律判断。
const scienceCards = [
  {
    title: '面试让交培训费 / 押金',
    scene: '面试最后一步说「先交培训费，入职后返还」，或要求交押金、服装费、材料费。',
    action:
      '不交、不签、不下载对方指定的 App。保存聊天记录、转账凭证和协议，向招聘平台、12333 或公安举报。'
  },
  {
    title: '招聘方和签约方不是同一家公司',
    scene: 'JD 写的是 A 公司，面试邀约、合同或收款方却变成 B 公司、C 培训机构。',
    action:
      '这是招转培的典型特征。先核对合同甲方、收款方、放款方；任何一方不一致都先停，不要签字或转账。'
  },
  {
    title: '先学后付 / 费用可分期',
    scene: '对方说培训免费，但要求你在指定平台做「分期」「助学贷」，或代你操作贷款。',
    action:
      '查清借款主体和放款方，不要把身份证、银行卡、手机交给对方操作。任何「先贷款再上岗」都按高风险处理。'
  },
  {
    title: '零基础月入过万',
    scene: '不限学历、不限经验，承诺转正 8-15K、上不封顶。',
    action:
      '对照同城同岗的真实薪资；把薪资、岗位、工作内容写进合同。只有口头承诺、没有书面约定时不要相信。'
  },
  {
    title: '岗前培训本身不是问题',
    scene: '正规企业也会写「带薪岗前培训」「入职后培训」。',
    action:
      '判断标准是它是否与收费、贷款、包就业、录用结果绑定。免费、入职后、本公司实施、不与录用挂钩的培训，通常属于正常安排。'
  },
  {
    title: '已经付款了怎么办',
    scene: '已经交了钱、签了协议，或被引导办了分期。',
    action:
      '立刻保存时间线证据：聊天记录、转账记录、合同、对方账户、宣传页面截图。先联系平台冻结，再向 12333、公安或市场监管部门反映。'
  }
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getPhrases()
  } catch (err) {
    error.value =
      err?.response?.data?.detail || err?.message || '词库加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function barWidth(count) {
  return `${Math.round((count / maxHits.value) * 100)}%`
}

onMounted(load)
</script>

<template>
  <div class="page">
    <section class="hero">
      <span class="hero-kicker">F-08 · 风险话术词库与科普卡</span>
      <h1 class="hero-title">风险话术不是玄学，是可以逐条对照的。</h1>
      <p class="hero-sub">
        词条以人社部等五部门「招转培 / 培训贷」风险提示原文为基础，并用项目标注集补齐真实变体。
        命中频次统计自 168 条标注 JD，不是模拟数字。
      </p>
    </section>

    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      show-icon
    />

    <section v-if="loading" class="card">
      <el-skeleton :rows="6" animated />
    </section>

    <template v-if="data && !loading">
      <section class="card">
        <div class="card-head">
          <h2>词库概览</h2>
          <span class="muted">v{{ meta.version || '—' }}</span>
        </div>
        <div class="report-grid">
          <div class="report-stat">
            <div class="stat-label">风险类别</div>
            <div class="stat-value">{{ categories.length }}</div>
          </div>
          <div class="report-stat">
            <div class="stat-label">词条总数</div>
            <div class="stat-value">{{ data.total_words }}</div>
          </div>
          <div class="report-stat">
            <div class="stat-label">标注集命中</div>
            <div class="stat-value">{{ totalHits }} 次</div>
          </div>
        </div>
        <p class="rule-note">
          统计语料：{{ corpus.positive }} 条正样本 + {{ corpus.negative }} 条真实招聘负样本，
          共 {{ corpus.size }} 条。每个类别可命中多次。
        </p>
      </section>

      <section class="phrase-grid">
        <article
          v-for="category in categories"
          :key="category.type"
          class="phrase-card"
        >
          <header class="phrase-head">
            <h3>{{ category.type }}</h3>
            <span class="weight-tag">建议扣 {{ category.weight }} 分</span>
          </header>
          <p class="phrase-basis">{{ category.official_basis }}</p>
          <div class="word-tags">
            <el-tag
              v-for="word in category.words"
              :key="word"
              size="small"
              effect="plain"
            >
              {{ word }}
            </el-tag>
          </div>
          <div class="freq-row">
            <span>标注集命中 {{ category.corpus_hits }} 次</span>
            <span class="muted">{{ category.word_count }} 个词条</span>
          </div>
          <div class="freq-track">
            <div class="freq-fill" :style="{ width: barWidth(category.corpus_hits) }"></div>
          </div>
        </article>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>科普卡</h2>
          <span class="muted">遇到这些场景，先停一下</span>
        </div>
        <div class="science-grid">
          <article
            v-for="(card, index) in scienceCards"
            :key="card.title"
            class="science-card"
          >
            <span class="science-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <h3>{{ card.title }}</h3>
            <p class="science-scene">{{ card.scene }}</p>
            <p class="science-action">{{ card.action }}</p>
          </article>
        </div>
        <p class="rule-note">
          以上为公开风险提示与项目规则的通俗说明，不构成法律意见。
          遇到具体纠纷，请保留证据并联系 12333、公安机关或市场监管部门。
        </p>
      </section>
    </template>
  </div>
</template>
