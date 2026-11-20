<template>
  <div class="page">
    <section class="hero">
      <span class="hero-kicker">面向大专院校在校生与应届毕业生</span>
      <h1 class="hero-title">
        把 JD 里的「宣称」，和能查到的「主体事实」逐一摆在一起看。
      </h1>
      <p class="hero-sub">
        粘贴一段招聘 JD 与公司名称，系统输出岗位风险、主体可信度、两者是否自洽的可解释结论。
        不要求注册登录；未识别到公司名称时，也可以先做岗位侧筛查。
      </p>
    </section>

    <section class="entry-grid">
      <RouterLink to="/analyze" class="entry-card">
        <h3>粘贴 JD 开始核验</h3>
        <p>风险话术原文高亮 + 公司证据 + JD—主体一致性校验，一次输出决策报告。</p>
        <span class="entry-arrow">进入核验 →</span>
      </RouterLink>
      <RouterLink to="/analyze" class="entry-card">
        <h3>上传岗位截图</h3>
        <p>刷到可疑岗位随手截图。OCR 统一入口已预留，当前可先粘贴文本使用。</p>
        <span class="entry-arrow">上传截图 →</span>
      </RouterLink>
      <RouterLink to="/batch" class="entry-card">
        <h3>批量模式（老师视角）</h3>
        <p>一次粘贴多条 JD，输出风险分布、高风险清单与风险类别统计。</p>
        <span class="entry-arrow">进入批量 →</span>
      </RouterLink>
    </section>

    <section class="stages">
      <div class="stage">
        <span class="stage-index">01 / 投递前</span>
        <h4>静态筛查</h4>
        <p>岗位话术风险、主体可信度、两侧是否自洽，逐条给出依据与扣分。</p>
      </div>
      <div class="stage">
        <span class="stage-index">02 / 过程中</span>
        <h4>主体监测</h4>
        <p>对照面试邀约、协议、付款截图的签约方，识别招聘方与签约方分离。</p>
      </div>
      <div class="stage">
        <span class="stage-index">03 / 事后</span>
        <h4>证据留存</h4>
        <p>汇总每条结论的证据链，便于向平台、12333 或公安提交时间线材料。</p>
      </div>
    </section>

    <p class="rule-note">
      想看每类风险话术的原文依据和应对办法？
      <RouterLink to="/phrases">查看风险话术词库与科普卡 →</RouterLink>
    </p>
  </div>
</template>
