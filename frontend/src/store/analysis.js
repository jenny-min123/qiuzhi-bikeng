import { defineStore } from 'pinia'
import { analyze, analyzeStream, getReport } from '../api'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    report: null,
    loading: false,
    progress: [],
    error: ''
  }),

  actions: {
    reset() {
      this.report = null
      this.loading = false
      this.progress = []
      this.error = ''
    },

    async run(jdText, companyName) {
      this.loading = true
      this.report = null
      this.progress = []
      this.error = ''

      const payload = {
        jd_text: jdText,
        company_name: companyName || null,
        images: []
      }

      try {
        await analyzeStream(payload, {
          onProgress: (data) => {
            if (data?.message) this.progress.push(data.message)
          },
          onReport: (data) => {
            this.report = data
          }
        })
        if (!this.report) throw new Error('未收到分析结果')
      } catch (streamError) {
        // SSE 不可用时退回普通 POST（全栈方案 2.4 的降级方案）
        try {
          this.report = await analyze(payload)
        } catch (error) {
          this.error =
            error?.response?.data?.detail || error?.message || '分析失败，请稍后重试'
        }
      } finally {
        this.loading = false
      }
    },

    async loadReport(reportId) {
      this.error = ''
      try {
        this.report = await getReport(reportId)
      } catch (error) {
        this.error =
          error?.response?.data?.detail || error?.message || '报告加载失败'
      }
    }
  }
})
