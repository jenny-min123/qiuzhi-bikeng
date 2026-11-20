<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { checkSubject, ocrImage } from '../api'

const text = ref('')
const recruiter = ref('')
const loading = ref(false)
const ocrLoading = ref(false)
const result = ref(null)
const error = ref('')

const severityMeta = {
  low: { label: '主体一致', className: 'verdict-accept' },
  medium: { label: '需要核实', className: 'verdict-caution' },
  high: { label: '风险较高', className: 'verdict-reject' },
  critical: { label: '签约方不一致', className: 'verdict-reject' },
  unknown: { label: '信息不足', className: 'verdict-caution' }
}

const meta = computed(
  () => severityMeta[result.value?.severity] || severityMeta.unknown
)

async function handleUpload(uploadFile) {
  const file = uploadFile?.raw
  if (!file || loading.value) return
  ocrLoading.value = true
  try {
    const data = await ocrImage(file)
    if (data.text) {
      text.value = data.text
      ElMessage.success(
        data.entities?.length
          ? `已识别 ${data.entities.length} 个公司主体`
          : '已识别截图文本'
      )
    } else {
      ElMessage.warning('未识别到文字，请换一张更清晰的截图或手动粘贴')
    }
  } catch (err) {
    ElMessage.warning(
      err?.response?.data?.detail || 'OCR 暂不可用，请手动粘贴文字'
    )
  } finally {
    ocrLoading.value = false
  }
}

async function submit() {
  if (!text.value.trim()) {
    ElMessage.warning('请先粘贴面试邀约、协议或收款页面中的文字')
    return
  }
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await checkSubject({
      text: text.value,
      recruiter_company: recruiter.value.trim() || null
    })
  } catch (err) {
    error.value =
      err?.response?.data?.detail || err?.message || '核验失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <section class="hero">
      <span class="hero-kicker">F-06 · 求职过程中主体监测</span>
      <h1 class="hero-title">招聘方是 A，签约方却变成了 B？</h1>
      <p class="hero-sub">
        把面试邀约、实习协议或收款页面上的文字粘贴进来，系统会提取其中的公司全称，
        与你登记的招聘方逐一对比。招聘方与签约方不是同一主体，是招转培的典型特征。
      </p>
    </section>

    <section class="card">
      <div class="card-head">
        <h2>录入材料</h2>
        <span class="muted">可粘贴文字，也可上传截图本地 OCR</span>
      </div>

      <label class="input-label" for="subject-text">邀约 / 协议 / 收款页面文字</label>
      <el-input
        id="subject-text"
        v-model="text"
        type="textarea"
        :rows="9"
        resize="vertical"
        placeholder="例如：甲方：XX教育科技有限公司；乙方：……&#10;收款方：……&#10;请粘贴与签约、收款相关的原文。"
      />

      <div class="input-row">
        <div>
          <label class="input-label" for="recruiter">招聘方公司全称（建议填写）</label>
          <el-input
            id="recruiter"
            v-model="recruiter"
            placeholder="发布 JD / 通知面试的公司全称"
            clearable
          />
        </div>
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          :on-change="handleUpload"
        >
          <el-button :loading="ocrLoading">上传截图 OCR</el-button>
        </el-upload>

        <el-button type="primary" :loading="loading" @click="submit">
          核对主体
        </el-button>
      </div>

      <p class="rule-hint">
        核心判断只依赖主体名同一性，不需要工商数据。
        全称一致或明确的分支机构会判为一致；名称相近但主体不同会告警。
        OCR 在本机运行，图片不会上传到第三方服务。
      </p>
    </section>

    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      show-icon
    />

    <section v-if="result" class="card">
      <div :class="['verdict-banner', meta.className]">
        <div class="verdict-title">{{ meta.label }}</div>
      </div>

      <p class="subject-alert">{{ result.alert }}</p>

      <div v-if="result.entities.length" class="subject-entities">
        <div class="card-head">
          <h3>识别到的主体</h3>
          <span class="muted">{{ result.entities.length }} 个</span>
        </div>
        <ul class="entity-list">
          <li
            v-for="entity in result.entities"
            :key="entity.name"
            class="subject-entity"
          >
            <span class="entity-name">{{ entity.name }}</span>
            <span
              v-if="entity.matches_recruiter === true"
              class="match-tag match-ok"
            >
              与招聘方一致
            </span>
            <span
              v-else-if="entity.matches_recruiter === false"
              class="match-tag match-bad"
            >
              与招聘方不一致
            </span>
            <span v-else class="match-tag match-unknown">待核对</span>
          </li>
        </ul>
      </div>

      <div v-if="result.advice.length" class="subject-advice">
        <h3>建议</h3>
        <ol class="advice-list">
          <li v-for="item in result.advice" :key="item">{{ item }}</li>
        </ol>
      </div>

      <p class="disclaimer">
        本结果为辅助提示，不构成对任何企业的事实认定或法律判断。
        遇到具体纠纷，请保留证据并联系 12333、公安机关或市场监管部门。
      </p>
    </section>
  </div>
</template>
