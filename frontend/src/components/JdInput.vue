<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import { ocrImage } from '../api'

const props = defineProps({
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['submit'])

const jdText = ref('')
const companyName = ref('')
const ocrLoading = ref(false)

const SAMPLE_JD =
  'AI剪辑实训生，零基础可投，不限专业，月薪8-15K。入职前需完成3个月实训，费用可分期，取证后包上岗'

function fillSample() {
  jdText.value = SAMPLE_JD
}

function submit() {
  if (!jdText.value.trim()) {
    ElMessage.warning('请先粘贴 JD 文本')
    return
  }
  emit('submit', {
    jdText: jdText.value,
    companyName: companyName.value.trim()
  })
}

async function handleUpload(uploadFile) {
  const file = uploadFile?.raw
  if (!file || props.loading) return
  ocrLoading.value = true
  try {
    const result = await ocrImage(file)
    if (result.text) {
      jdText.value = result.text
      ElMessage.success('已识别截图文本')
    } else {
      ElMessage.warning('截图中未识别到文本，请手动粘贴')
    }
  } catch (error) {
    ElMessage.warning(
      error?.response?.data?.detail || 'OCR 暂不可用，请手动粘贴 JD 文本'
    )
  } finally {
    ocrLoading.value = false
  }
}
</script>

<template>
  <section class="card input-card">
    <div class="card-head">
      <h2>岗位信息</h2>
      <button class="sample-link" type="button" @click="fillSample">
        填入示例 JD
      </button>
    </div>

    <label class="input-label" for="jd-text">招聘 JD 原文</label>
    <el-input
      id="jd-text"
      v-model="jdText"
      type="textarea"
      :rows="10"
      resize="vertical"
      placeholder="粘贴招聘 JD 原文。系统会保留原文，并把命中风险话术的位置高亮出来。"
    />

    <div class="input-row">
      <div>
        <label class="input-label" for="company-name">公司名称（可留空）</label>
        <el-input
          id="company-name"
          v-model="companyName"
          placeholder="例如：深圳市某某网络科技有限公司"
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
        开始核验
      </el-button>
    </div>

    <p class="rule-hint">
      留空公司名称时只做岗位侧话术筛查；填写后才会执行主体核验与一致性校验。
    </p>
  </section>
</template>

<style scoped>
.sample-link {
  border: none;
  background: none;
  color: var(--accent);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}

.sample-link:hover {
  text-decoration: underline;
}

.rule-hint {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--muted);
}
</style>
