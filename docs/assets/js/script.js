/* ==========================================================================
   MAHARASHTRA HIGH SCHOOL, CHIPLUN — MAIN JAVASCRIPT
   UDISE: 27320100147 | Muradpur Campus, Chiplun
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initImageSkeletons();
  initTickerDismiss();
  initNavigation();
  initMultilingualSupport();
  initRteCalculator();
  initAccordions();
  initAcademicTabs();
  initContactForm();
  initNoticeSearch();
  initBackToTop();
  initScrollReveal();
  initHeaderShrink();
  initNavOutsideClose();
  initDynamicSkeletons();
});

/* ── 1. Dismissable Ticker Bar ─────────────────────────────────── */
function initTickerDismiss() {
  const tickerBar = document.getElementById('announcementTicker');
  const closeBtn  = document.getElementById('tickerCloseBtn');

  if (sessionStorage.getItem('mhs_ticker_closed') === 'true') {
    if (tickerBar) tickerBar.style.display = 'none';
  }

  if (closeBtn && tickerBar) {
    closeBtn.addEventListener('click', () => {
      tickerBar.style.display = 'none';
      sessionStorage.setItem('mhs_ticker_closed', 'true');
    });
  }
}

/* ── 2. Multi-Page Navigation & Active Page Detector ───────────── */
function initNavigation() {
  const mobileToggle = document.getElementById('mobileToggle');
  const navMenu      = document.getElementById('navMenu');
  const navLinks     = document.querySelectorAll('.nav-link');

  let backdrop = document.querySelector('.nav-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.className = 'nav-backdrop';
    document.body.appendChild(backdrop);
  }

  function toggleMenu(forceClose = false) {
    if (!mobileToggle || !navMenu) return;
    const isOpening = !navMenu.classList.contains('active') && !forceClose;
    navMenu.classList.toggle('active', isOpening);
    mobileToggle.classList.toggle('open', isOpening);
    backdrop.classList.toggle('active', isOpening);
    document.body.style.overflow = isOpening ? 'hidden' : '';
  }

  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => toggleMenu());
  }
  if (backdrop) {
    backdrop.addEventListener('click', () => toggleMenu(true));
  }

  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    }
    // Close menu when a link is clicked
    link.addEventListener('click', () => {
      if (window.innerWidth <= 1200) toggleMenu(true);
    });
  });
}

/* ══════════════════════════════════════════════════════════════════
   3. FULL-SITE MULTILINGUAL SYSTEM
   ── data-i18n="key"        → replaces textContent
   ── data-i18n-html="key"   → replaces innerHTML (allows <em> etc.)
   ── data-i18n-attr="attr:key,attr2:key2"  → replaces attributes
   ── Language persisted in localStorage across page navigations
══════════════════════════════════════════════════════════════════ */

const t = {
  en: {
    /* Nav */
    "brand.title":           "Maharashtra High School",
    "brand.sub":             "Urdu · Muradpur, Chiplun",
    "nav.home":              "Home",
    "nav.about":             "About Us",
    "nav.academics":         "Academics",
    "nav.admissions":        "Admissions",
    "nav.rti":               "RTI Gazette",
    "nav.achievements":      "Achievements",
    "nav.contact":           "Contact",
    "nav.apply":             "Apply Now",
    /* Ticker */
    "ticker.notice":         "NOTICE",
    "ticker.text":           "Admissions Open 2026–27 · RTE 25% EWS Quota: Apply via student.maharashtra.gov.in · UDISE: 27320100147 · Haji A.E. Kalsekar Jr. College (Arts & Commerce) also on campus",
    /* Hero */
    "hero.tag":              "ESTABLISHED 1970 — CHIPLUN EDUCATION SOCIETY — MURADPUR, CHIPLUN",
    "hero.title":            "Over Five Decades of Urdu Medium Education in <em>Muradpur, Chiplun</em>",
    "hero.sub":              "Founded in 1970 by the Chiplun Education Society — itself established in 1961 by community leaders of Dadar Mohalla, Muradpur, Jam-e-Masjid Mohalla, and Mithagari Mohalla — Maharashtra High School began with two classrooms and grew into Chiplun's most trusted Urdu-medium secondary institution.",
    "hero.btn.primary":      "Check RTE Seat Eligibility →",
    "hero.btn.secondary":    "Our History & Faculty",
    "hero.caption.1":        "MURADPUR CAMPUS — EST. 1970",
    "hero.caption.2":        "UDISE: 27320100147",
    /* Metrics */
    "metric.1.num":          "1970",
    "metric.1.lbl":          "Year Founded — Chiplun Education Society (est. 1961)",
    "metric.2.num":          "27320100147",
    "metric.2.lbl":          "State UDISE Block Code (Ratnagiri District)",
    "metric.3.num":          "Std V – XII",
    "metric.3.lbl":          "Upper Primary → Higher Secondary Tracks",
    "metric.4.num":          "3,400+",
    "metric.4.lbl":          "Library Volumes — Campus Resource Centre",
    /* Homepage sections */
    "section.timeline.tag":  "CHIPLUN EDUCATION SOCIETY — INSTITUTIONAL TIMELINE",
    "section.timeline.h2":   "From Two Classrooms in 1970 to a Full Campus Cluster",
    "section.portal.tag":    "PORTAL DIRECTORY",
    "section.portal.h2":     "What You Can Do on This Portal",
    /* About page */
    "about.tag":             "INSTITUTIONAL HISTORY & CONTEXT",
    "about.h1":              "Maharashtra High School, Chiplun — A Half-Century of Service",
    /* Academics */
    "academics.tag":         "CURRICULUM & TIMETABLES — MSBSHSE PUNE DIVISION",
    "academics.h1":          "Academic Framework, Syllabus & Calendar 2026–27",
    /* Admissions */
    "admissions.tag":        "ONBOARDING & FEE SCHEDULE 2026–27",
    "admissions.h1":         "Student Admissions & Enrolment Portal",
    /* RTI */
    "rti.tag":               "SECTION 4(1)(B) — RIGHT TO INFORMATION ACT 2005",
    "rti.h1":                "Statutory Disclosures & Maharashtra RTI Rules 2026",
    /* Achievements */
    "achievements.tag":      "SSC BOARD RESULTS — MSBSHSE PUNE DIVISION",
    "achievements.h1":       "Academic Excellence Since 1970",
    /* Contact */
    "contact.tag":           "DIRECT COMMUNICATIONS — MURADPUR CAMPUS",
    "contact.h1":            "Contact Principal's Office & Campus Location",
    /* Footer */
    "footer.school":         "MAHARASHTRA HIGH SCHOOL",
    "footer.nav.head":       "NAVIGATION",
    "footer.campus.head":    "CAMPUS & SOCIETY",
    "footer.copy":           "© 2026 Maharashtra High School, Chiplun · UDISE: 27320100147 · Chiplun Education Society · Maharashtra State Board Recognized",
    /* Form */
    "form.name.label":       "PARENT / GUARDIAN FULL NAME *",
    "form.phone.label":      "10-DIGIT INDIAN MOBILE NUMBER *",
    "form.purpose.label":    "TARGET CLASS / PURPOSE *",
    "form.locality.label":   "YOUR RESIDENTIAL LOCALITY (CHIPLUN)",
    "form.message.label":    "SPECIFIC DETAILS / QUERIES",
    "form.submit":           "Submit Admission Inquiry →",
  },

  /* ════ URDU ════════════════════════════════════════════════════ */
  ur: {
    "brand.title":           "مہاراشٹرا ہائی اسکول، چپلُون",
    "brand.sub":             "اردو · مراد پور، چپلُون",
    "nav.home":              "ہوم",
    "nav.about":             "ہمارے بارے میں",
    "nav.academics":         "تعلیمی نظام",
    "nav.admissions":        "داخلہ",
    "nav.rti":               "آر ٹی آئی گزٹ",
    "nav.achievements":      "کامیابیاں",
    "nav.contact":           "رابطہ",
    "nav.apply":             "ابھی درخواست دیں",
    "ticker.notice":         "اطلاع",
    "ticker.text":           "داخلہ کھلا ہے ۲۰۲۶–۲۷ · آر ٹی ای ۲۵٪ ای ڈبلیو ایس: student.maharashtra.gov.in · UDISE: 27320100147",
    "hero.tag":              "قیام ۱۹۷۰ — چپلُون ایجوکیشن سوسائٹی — مراد پور",
    "hero.title":            "مراد پور، چپلُون میں <em>اردو میڈیم تعلیم</em> کی پچاس سالہ روایت",
    "hero.sub":              "چپلُون ایجوکیشن سوسائٹی نے ۱۹۷۰ میں اس اسکول کی بنیاد رکھی۔ سوسائٹی خود ۱۹۶۱ میں دادار محلہ، مراد پور، جامع مسجد محلہ اور میٹھاگری محلہ کے سرکردہ افراد نے قائم کی تھی۔ یہ اسکول دو کمروں سے شروع ہوا اور آج چپلُون کا سب سے معتبر اردو میڈیم ادارہ ہے۔",
    "hero.btn.primary":      "← آر ٹی ای نشست کی اہلیت چیک کریں",
    "hero.btn.secondary":    "ہماری تاریخ اور اساتذہ",
    "hero.caption.1":        "مراد پور کیمپس — قیام ۱۹۷۰",
    "hero.caption.2":        "UDISE: 27320100147",
    "metric.1.num":          "۱۹۷۰",
    "metric.1.lbl":          "سال قیام — چپلُون ایجوکیشن سوسائٹی (قائم ۱۹۶۱)",
    "metric.2.num":          "27320100147",
    "metric.2.lbl":          "ریاستی یو ڈی آئی ایس ای کوڈ (رتناگیری ضلع)",
    "metric.3.num":          "جماعت ۵ تا ۱۲",
    "metric.3.lbl":          "ابتدائی سے اعلیٰ ثانوی تک",
    "metric.4.num":          "۳٬۴۰۰+",
    "metric.4.lbl":          "کتب خانے میں کتابیں — کیمپس ریسورس سنٹر",
    "section.timeline.tag":  "چپلُون ایجوکیشن سوسائٹی — ادارہ جاتی سفر",
    "section.timeline.h2":   "۱۹۷۰ میں دو کمروں سے آج کے مکمل کیمپس تک",
    "section.portal.tag":    "پورٹل رہنمائی",
    "section.portal.h2":     "اس ویب سائٹ پر آپ کیا کر سکتے ہیں",
    "about.tag":             "ادارہ جاتی تاریخ و پس منظر",
    "about.h1":              "مہاراشٹرا ہائی اسکول، چپلُون — نصف صدی کی خدمت",
    "academics.tag":         "نصاب اور ٹائم ٹیبل — ایم ایس بی ایس ایچ ایس ای پونے ڈویژن",
    "academics.h1":          "تعلیمی ڈھانچہ، نصاب اور تقویم ۲۰۲۶–۲۷",
    "admissions.tag":        "داخلہ اور فیس ۲۰۲۶–۲۷",
    "admissions.h1":         "طلباء داخلہ پورٹل",
    "rti.tag":               "دفعہ ۴(۱)(ب) — حق اطلاعات ایکٹ ۲۰۰۵",
    "rti.h1":                "قانونی انکشافات اور مہاراشٹرا آر ٹی آئی قواعد ۲۰۲۶",
    "achievements.tag":      "ایس ایس سی بورڈ نتائج — ایم ایس بی ایس ایچ ایس ای",
    "achievements.h1":       "۱۹۷۰ سے علمی فضیلت کا سلسلہ",
    "contact.tag":           "براہ راست رابطہ — مراد پور کیمپس",
    "contact.h1":            "پرنسپل آفس اور کیمپس کا مقام",
    "footer.school":         "مہاراشٹرا ہائی اسکول",
    "footer.nav.head":       "روابط",
    "footer.campus.head":    "کیمپس اور سوسائٹی",
    "footer.copy":           "© ۲۰۲۶ مہاراشٹرا ہائی اسکول، چپلُون · UDISE: 27320100147 · چپلُون ایجوکیشن سوسائٹی",
    "form.name.label":       "والدین / سرپرست کا پورا نام *",
    "form.phone.label":      "۱۰ ہندسوں کا موبائل نمبر *",
    "form.purpose.label":    "مقصد / جماعت *",
    "form.locality.label":   "آپ کا رہائشی محلہ (چپلُون)",
    "form.message.label":    "تفصیلی سوال",
    "form.submit":           "← پرنسپل آفس کو درخواست بھیجیں",
  },

  /* ════ MARATHI ══════════════════════════════════════════════════ */
  mr: {
    "brand.title":           "महाराष्ट्र हायस्कूल, चिपळूण",
    "brand.sub":             "उर्दू · मुरादपूर, चिपळूण",
    "nav.home":              "मुख्यपृष्ठ",
    "nav.about":             "आमच्याबद्दल",
    "nav.academics":         "शैक्षणिक",
    "nav.admissions":        "प्रवेश",
    "nav.rti":               "RTI राजपत्र",
    "nav.achievements":      "यश",
    "nav.contact":           "संपर्क",
    "nav.apply":             "आता अर्ज करा",
    "ticker.notice":         "सूचना",
    "ticker.text":           "प्रवेश सुरू आहेत २०२६–२७ · RTE २५% EWS कोटा: student.maharashtra.gov.in · UDISE: 27320100147",
    "hero.tag":              "स्थापना १९७० — चिपळूण एज्युकेशन सोसायटी — मुरादपूर, चिपळूण",
    "hero.title":            "मुरादपूर, चिपळूण येथे <em>उर्दू माध्यम शिक्षणाची</em> पन्नास वर्षांची परंपरा",
    "hero.sub":              "१९७० मध्ये चिपळूण एज्युकेशन सोसायटीने स्थापन केलेल्या या शाळेची सुरुवात फक्त दोन वर्गखोल्यांनी झाली. सोसायटी स्वतः १९६१ मध्ये दादर मोहल्ला, मुरादपूर, जामा मशीद मोहल्ला आणि मिठागरी मोहल्ल्याच्या प्रतिष्ठित नागरिकांनी स्थापन केली होती.",
    "hero.btn.primary":      "RTE जागेची पात्रता तपासा →",
    "hero.btn.secondary":    "आमचा इतिहास व शिक्षक",
    "hero.caption.1":        "मुरादपूर कॅम्पस — स्था. १९७०",
    "hero.caption.2":        "UDISE: 27320100147",
    "metric.1.num":          "१९७०",
    "metric.1.lbl":          "स्थापना वर्ष — चिपळूण एज्युकेशन सोसायटी (स्था. १९६१)",
    "metric.2.num":          "27320100147",
    "metric.2.lbl":          "राज्य UDISE कोड (रत्नागिरी जिल्हा)",
    "metric.3.num":          "इयत्ता V – XII",
    "metric.3.lbl":          "उच्च प्राथमिक → उच्च माध्यमिक",
    "metric.4.num":          "३,४००+",
    "metric.4.lbl":          "ग्रंथालय पुस्तके — कॅम्पस संसाधन केंद्र",
    "section.timeline.tag":  "चिपळूण एज्युकेशन सोसायटी — संस्थात्मक कालक्रम",
    "section.timeline.h2":   "१९७० मधील दोन वर्गखोल्यांपासून आजच्या पूर्ण कॅम्पसपर्यंत",
    "section.portal.tag":    "पोर्टल निर्देशिका",
    "section.portal.h2":     "या पोर्टलवर आपण काय करू शकता",
    "about.tag":             "संस्थात्मक इतिहास व संदर्भ",
    "about.h1":              "महाराष्ट्र हायस्कूल, चिपळूण — अर्धशतकाची सेवा",
    "academics.tag":         "अभ्यासक्रम व वेळापत्रक — MSBSHSE पुणे विभाग",
    "academics.h1":          "शैक्षणिक आराखडा, अभ्यासक्रम व दिनदर्शिका २०२६–२७",
    "admissions.tag":        "प्रवेश व शुल्क २०२६–२७",
    "admissions.h1":         "विद्यार्थी प्रवेश पोर्टल",
    "rti.tag":               "कलम ४(१)(ब) — माहितीचा अधिकार अधिनियम २००५",
    "rti.h1":                "वैधानिक प्रकटीकरण व महाराष्ट्र RTI नियम २०२६",
    "achievements.tag":      "SSC बोर्ड निकाल — MSBSHSE पुणे विभाग",
    "achievements.h1":       "१९७० पासून शैक्षणिक उत्कृष्टता",
    "contact.tag":           "थेट संपर्क — मुरादपूर कॅम्पस",
    "contact.h1":            "मुख्याध्यापक कार्यालय व कॅम्पसचे स्थान",
    "footer.school":         "महाराष्ट्र हायस्कूल",
    "footer.nav.head":       "नेव्हिगेशन",
    "footer.campus.head":    "कॅम्पस व सोसायटी",
    "footer.copy":           "© २०२६ महाराष्ट्र हायस्कूल, चिपळूण · UDISE: 27320100147 · चिपळूण एज्युकेशन सोसायटी",
    "form.name.label":       "पालक / पाल्याचे पूर्ण नाव *",
    "form.phone.label":      "१०-अंकी भारतीय मोबाइल नंबर *",
    "form.purpose.label":    "उद्देश / इयत्ता *",
    "form.locality.label":   "आपला निवासी विभाग (चिपळूण)",
    "form.message.label":    "विशिष्ट प्रश्न / तपशील",
    "form.submit":           "मुख्याध्यापक कार्यालयाला चौकशी पाठवा →",
  }
};

/* Urdu & Marathi body font overrides */
(function injectLangStyles() {
  const style = document.createElement('style');
  style.id = 'lang-font-overrides';
  style.textContent = `
    body.lang-urdu, body.lang-urdu p, body.lang-urdu h1, body.lang-urdu h2,
    body.lang-urdu h3, body.lang-urdu h4, body.lang-urdu .nav-link,
    body.lang-urdu .brand-title, body.lang-urdu .brand-sub,
    body.lang-urdu .section-headline, body.lang-urdu .hero-title,
    body.lang-urdu .hero-subtitle, body.lang-urdu .bento-desc,
    body.lang-urdu .faculty-bio, body.lang-urdu .metric-lbl,
    body.lang-urdu td, body.lang-urdu li {
      font-family: 'Noto Naskh Arabic', serif !important;
      letter-spacing: 0 !important;
    }
    body.lang-marathi, body.lang-marathi p, body.lang-marathi h1,
    body.lang-marathi h2, body.lang-marathi h3, body.lang-marathi h4,
    body.lang-marathi .brand-title, body.lang-marathi .hero-title,
    body.lang-marathi .section-headline, body.lang-marathi .hero-subtitle,
    body.lang-marathi .bento-desc, body.lang-marathi .faculty-bio,
    body.lang-marathi td, body.lang-marathi li {
      font-family: 'Noto Sans Devanagari', sans-serif !important;
    }
  `;
  document.head.appendChild(style);
})();

function initMultilingualSupport() {
  const langBtns = document.querySelectorAll('.lang-btn');

  const saved = localStorage.getItem('mhs_lang') || 'en';
  if (saved !== 'en') {
    langBtns.forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-lang') === saved);
    });
    applyLanguage(saved, false);
  }

  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.getAttribute('data-lang');
      langBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      localStorage.setItem('mhs_lang', lang);
      applyLanguage(lang, true);
    });
  });
}

function applyLanguage(lang, showToastMsg = false) {
  const data = t[lang];
  if (!data) return;

  document.documentElement.lang = lang;
  document.documentElement.dir  = lang === 'ur' ? 'rtl' : 'ltr';

  document.body.classList.toggle('lang-urdu',    lang === 'ur');
  document.body.classList.toggle('lang-marathi', lang === 'mr');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (data[key] !== undefined) el.textContent = data[key];
  });

  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    if (data[key] !== undefined) el.innerHTML = data[key];
  });

  document.querySelectorAll('[data-i18n-attr]').forEach(el => {
    el.getAttribute('data-i18n-attr').split(',').forEach(pair => {
      const [attr, key] = pair.trim().split(':');
      if (data[key] !== undefined) el.setAttribute(attr.trim(), data[key]);
    });
  });

  if (showToastMsg) {
    const labels = { en: 'English', ur: 'اردو — Urdu', mr: 'मराठी — Marathi' };
    showToast(labels[lang] || lang);
  }
}

/* ── 4. Interactive RTE Eligibility Estimator ──────────────────── */
function initRteCalculator() {
  const calcBtn      = document.getElementById('btnCalculateRte');
  const incomeInput  = document.getElementById('calcIncome');
  const categorySelect = document.getElementById('calcCategory');
  const resultBox    = document.getElementById('calcResult');

  if (calcBtn && incomeInput && categorySelect && resultBox) {
    calcBtn.addEventListener('click', () => {
      const income   = parseFloat(incomeInput.value);
      const category = categorySelect.value;

      if (isNaN(income) || income < 0) {
        showToast('Please enter an annual income amount to calculate eligibility.', 'error');
        return;
      }

      const isIncomeEligible = income <= 100000;
      const isDgCategory     = ['SC','ST','OBC_NCL','PWD'].includes(category);

      if (isIncomeEligible || isDgCategory) {
        resultBox.className = 'calc-result-box eligible';
        resultBox.innerHTML = `
          <strong>QUALIFIED FOR RTE 25% EWS SEAT ALLOCATION</strong><br>
          Based on annual income of ₹${income.toLocaleString('en-IN')}, your child qualifies under Maharashtra RTE Section 12(1)(c) for <strong>100% Tuition Fee Exemption</strong>.<br>
          <a href="https://student.maharashtra.gov.in" target="_blank" rel="noopener" style="color:var(--status-success);font-weight:700;text-decoration:underline;display:inline-block;margin-top:0.5rem;">
            Proceed to Official Maharashtra RTE Portal →
          </a>
        `;
      } else {
        resultBox.className = 'calc-result-box not-eligible';
        resultBox.innerHTML = `
          <strong>REGULAR STATE BOARD ADMISSION TRACK APPLICABLE</strong><br>
          Annual income exceeds the ₹1,00,000 threshold. You may apply under the standard State Board track.<br>
          <a href="admissions.html#fee-structure" style="color:var(--status-alert);font-weight:700;text-decoration:underline;display:inline-block;margin-top:0.5rem;">
            View Approved Regular Fee Matrix ↓
          </a>
        `;
      }
    });
  }
}

/* ── 5. Accordions ─────────────────────────────────────────────── */
function initAccordions() {
  document.querySelectorAll('.accordion-header').forEach(header => {
    header.addEventListener('click', () => {
      const item     = header.parentElement;
      const isActive = item.classList.contains('active');
      document.querySelectorAll('.accordion-item').forEach(i => i.classList.remove('active'));
      if (!isActive) item.classList.add('active');
    });
  });
}

/* ── 6. Academic Tabs ───────────────────────────────────────────── */
function initAcademicTabs() {
  const tabBtns     = document.querySelectorAll('.academic-btn');
  const tabContents = document.querySelectorAll('.academic-tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      tabBtns.forEach(b    => b.classList.remove('active'));
      tabContents.forEach(c => c.style.display = 'none');
      btn.classList.add('active');
      const target = document.getElementById(tabId);
      if (target) target.style.display = 'block';
    });
  });
}

/* ── 7. Contact & Admission Form Validation ────────────────────── */
function initContactForm() {
  const form       = document.getElementById('inquiryForm');
  const phoneInput = document.getElementById('inqPhone');
  const phoneError = document.getElementById('phoneErrorMsg');
  const phoneRegex = /^[6-9]\d{9}$/;

  if (phoneInput && phoneError) {
    phoneInput.addEventListener('input', () => {
      const val = phoneInput.value.trim();
      const invalid = val && !phoneRegex.test(val);
      phoneInput.classList.toggle('invalid-field', invalid);
      phoneError.classList.toggle('visible', invalid);
    });
  }

  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const name   = document.getElementById('inqName')?.value.trim()    || '';
      const phone  = phoneInput?.value.trim()                              || '';
      const cls    = document.getElementById('inqClass')?.value           || '';
      const msg    = document.getElementById('inqMessage')?.value.trim()  || '';

      if (!phoneRegex.test(phone)) {
        phoneInput?.classList.add('invalid-field');
        phoneError?.classList.add('visible');
        showToast('Please enter a valid 10-digit Indian mobile number.', 'error');
        return;
      }

      const inquiry = { id: Date.now(), date: new Date().toLocaleString('en-IN'), name, phone, cls, msg };
      const existing = JSON.parse(localStorage.getItem('mhs_inquiries_v1') || '[]');
      existing.push(inquiry);
      localStorage.setItem('mhs_inquiries_v1', JSON.stringify(existing));

      showToast('Inquiry submitted to Principal\'s Office', 'success');
      form.reset();
      phoneInput?.classList.remove('invalid-field');
      phoneError?.classList.remove('visible');
    });
  }
}

/* ── 8. Notice Search ──────────────────────────────────────────── */
function initNoticeSearch() {
  const searchInput = document.getElementById('noticeSearchInput');
  const noticeItems = document.querySelectorAll('.notice-list-item');

  if (searchInput) {
    searchInput.addEventListener('input', e => {
      const q = e.target.value.toLowerCase();
      noticeItems.forEach(item => {
        item.style.display = item.innerText.toLowerCase().includes(q) ? 'flex' : 'none';
      });
    });
  }
}

/* ── 9. Back to Top ────────────────────────────────────────────── */
function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;

  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.pageYOffset > 400);
  }, { passive: true });

  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

/* ── 10. Scroll-Reveal (staggered IntersectionObserver) ─────────── */
function initScrollReveal() {
  const targets = document.querySelectorAll(
    '.faculty-card, .bento-cell, .metric-panel-cell, .gallery-item, .pio-card'
  );
  targets.forEach((el, i) => {
    el.classList.add('reveal-on-scroll');
    el.style.transitionDelay = `${(i % 4) * 70}ms`;
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -32px 0px' });

  targets.forEach(el => observer.observe(el));
}

/* ── 11. Header Shadow on Scroll ───────────────────────────────── */
function initHeaderShrink() {
  const header = document.getElementById('mainHeader');
  if (!header) return;

  let shrunk = false;
  window.addEventListener('scroll', () => {
    const should = window.scrollY > 60;
    if (should !== shrunk) {
      shrunk = should;
      header.style.boxShadow  = shrunk ? '0 2px 12px rgba(0,0,0,0.06)' : '';
      header.style.transition = 'box-shadow 240ms';
    }
  }, { passive: true });
}

/* ── 12. Nav Close on Outside Click ────────────────────────────── */
function initNavOutsideClose() {
  const navMenu      = document.getElementById('navMenu');
  const mobileToggle = document.getElementById('mobileToggle');
  const backdrop     = document.querySelector('.nav-backdrop');
  if (!navMenu || !mobileToggle) return;

  document.addEventListener('click', e => {
    if (navMenu.classList.contains('active') &&
        !navMenu.contains(e.target) &&
        !mobileToggle.contains(e.target)) {
      navMenu.classList.remove('active');
      mobileToggle.classList.remove('open');
      if (backdrop) backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
}

/* ── Toast Helper ───────────────────────────────────────────────── */
function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id        = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  if (type === 'error')   toast.style.borderLeftColor = '#991B1B';
  if (type === 'success') toast.style.borderLeftColor = '#166534';

  toast.innerHTML = `<div>${message}</div>`;
  container.appendChild(toast);

  toast.style.opacity   = '0';
  toast.style.transform = 'translateX(12px)';
  requestAnimationFrame(() => {
    toast.style.transition = 'opacity 200ms, transform 200ms';
    toast.style.opacity    = '1';
    toast.style.transform  = 'translateX(0)';
  });

  setTimeout(() => {
    toast.style.opacity   = '0';
    toast.style.transform = 'translateX(12px)';
    setTimeout(() => toast.remove(), 220);
  }, 4000);
}

/* ── 13. Image Skeleton Loader ───────────────────────────────────
   Wraps images in an active shimmer skeleton container until the
   image has fully loaded, eliminating layout shift and providing
   smooth fade-in across all pages.                             */
function initImageSkeletons() {
  const images = document.querySelectorAll('img');

  images.forEach(img => {
    if (img.parentElement && img.parentElement.classList.contains('img-skeleton-wrapper')) {
      return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'img-skeleton-wrapper';

    if (img.style.height) wrapper.style.height = img.style.height;
    if (img.className.includes('brand-logo')) {
      wrapper.style.width = '40px';
      wrapper.style.height = '40px';
      wrapper.style.flexShrink = '0';
    }

    img.parentNode.insertBefore(wrapper, img);
    wrapper.appendChild(img);

    const markLoaded = () => {
      wrapper.classList.add('loaded');
    };

    if (img.complete && img.naturalWidth > 0) {
      markLoaded();
    } else {
      img.addEventListener('load', markLoaded, { once: true });
      img.addEventListener('error', markLoaded, { once: true });
    }
  });
}

/* ── 14. Dynamic Micro-Skeletons & Text Skeleton Loader ─────────── */
function initDynamicSkeletons() {
  const tabBtns = document.querySelectorAll('.academic-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      const target = document.getElementById(tabId);
      if (target) {
        target.style.opacity = '0';
        target.style.transform = 'translateY(4px)';
        requestAnimationFrame(() => {
          target.style.transition = 'opacity 180ms ease, transform 180ms ease';
          target.style.opacity = '1';
          target.style.transform = 'translateY(0)';
        });
      }
    });
  });

  // Global demo helper: allows user to toggle text + image skeleton state on demand
  window.toggleSkeletonDemo = function(durationMs = 3000) {
    // 1. Unload all image wrappers
    const wrappers = document.querySelectorAll('.img-skeleton-wrapper');
    wrappers.forEach(w => w.classList.remove('loaded'));

    // 2. Activate skeleton-loading on entire body (all text, titles, paragraphs, tables, links)
    document.body.classList.add('skeleton-loading');

    showToast('Universal skeleton preview active (ALL text & images) for ' + (durationMs / 1000) + 's');

    setTimeout(() => {
      // Re-load images
      wrappers.forEach(w => w.classList.add('loaded'));
      // Remove skeleton-loading from body to reveal all text
      document.body.classList.remove('skeleton-loading');
    }, durationMs);
  };
}

