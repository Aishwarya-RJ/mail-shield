/* ==========================================================================
   MAIL SHIELD - FRONTEND APPLICATION JAVASCRIPT
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM ELEMENTS ---
  const htmlDoc = document.documentElement;
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  
  // Navigation Buttons & Views
  const btnNavAnalyzer = document.getElementById('btnNavAnalyzer');
  const btnNavBatch = document.getElementById('btnNavBatch');
  const btnNavMetrics = document.getElementById('btnNavMetrics');
  
  const viewVerifier = document.getElementById('viewVerifier');
  const viewBatch = document.getElementById('viewBatch');
  const viewMetrics = document.getElementById('viewMetrics');
  
  // Verifier Elements
  const messageInput = document.getElementById('messageInput');
  const btnAnalyze = document.getElementById('btnAnalyze');
  const btnPasteText = document.getElementById('btnPasteText');
  const btnClearText = document.getElementById('btnClearText');
  const charCounter = document.getElementById('charCounter');
  const wordCounter = document.getElementById('wordCounter');
  const typingIndicator = document.getElementById('typingIndicator');
  
  // Results Elements
  const resultsPanel = document.getElementById('resultsPanel');
  const verdictCard = document.getElementById('verdictCard');
  const verdictIcon = document.getElementById('verdictIcon');
  const verdictLabel = document.getElementById('verdictLabel');
  const verdictTitle = document.getElementById('verdictTitle');
  const verdictDesc = document.getElementById('verdictDesc');
  const scoreRing = document.getElementById('scoreRing');
  const scorePercent = document.getElementById('scorePercent');
  
  const highlightedText = document.getElementById('highlightedText');
  const triggerCountPill = document.getElementById('triggerCountPill');
  
  const urgencyBar = document.getElementById('urgencyBar');
  const urgencyVal = document.getElementById('urgencyVal');
  const financialBar = document.getElementById('financialBar');
  const financialVal = document.getElementById('financialVal');
  const phishingBar = document.getElementById('phishingBar');
  const phishingVal = document.getElementById('phishingVal');
  const formattingBar = document.getElementById('formattingBar');
  const formattingVal = document.getElementById('formattingVal');
  
  const scoreLR = document.getElementById('scoreLR');
  const scoreNB = document.getElementById('scoreNB');
  const scoreRF = document.getElementById('scoreRF');
  
  const origRewriteText = document.getElementById('origRewriteText');
  const cleanRewriteText = document.getElementById('cleanRewriteText');
  const rewriteAdvice = document.getElementById('rewriteAdvice');
  const btnCopyCleanText = document.getElementById('btnCopyCleanText');

  // Batch Elements
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const btnBrowseFile = document.getElementById('btnBrowseFile');
  const batchResultsWrapper = document.getElementById('batchResultsWrapper');
  const batchTableBody = document.getElementById('batchTableBody');
  const batchCount = document.getElementById('batchCount');
  const btnClearBatch = document.getElementById('btnClearBatch');

  // Metrics Elements
  const metricAccLR = document.getElementById('metricAccLR');
  const metricAccNB = document.getElementById('metricAccNB');
  const metricAccRF = document.getElementById('metricAccRF');
  const topWordsCloud = document.getElementById('topWordsCloud');
  const statSpamCount = document.getElementById('statSpamCount');
  const statHamCount = document.getElementById('statHamCount');

  // --- STATE ---
  let typingTimer = null;

  // Preset Scenario Dictionary
  const PRESETS = {
    phishing: "Subject: FPA Notice : ebay misrepresentation of identity - user suspension\nDear ebay member, in an effort to protect your account security we have suspended your account until such time that it can be safely restored. Please click here to verify your identity and national credit card information.",
    prince: "Subject: Unbelievable new home loans made easy!\nYou have been pre-approved for a $454,169 cash loan at a 3.72% fixed rate. This offer is extended unconditionally. Click here now for your instant $10,000 cash bonus!",
    promo: "Subject: Save your money buy getting software CDs & meds here!\nHave you tried Cialis or Viagra yet? Great erection guaranteed within 10 minutes. Click here right now to save 75% on Norton Internet Security and Microsoft Windows XP!",
    meeting: "Subject: Team sync & quarterly roadmap discussion\nHi team, please find the meeting notes and project architecture deck for tomorrow's 10:00 AM sync. Let me know if anyone has questions before the call.",
    receipt: "Subject: Order Confirmation #893021 - Golden Graphix\nThank you for your order. Your invoice details are attached in PDF format. Tracking information will be emailed once your package ships."
  };

  // --- THEME SWITCHER ---
  const savedTheme = localStorage.getItem('mail_shield_theme') || localStorage.getItem('aura_theme') || 'dark';
  htmlDoc.setAttribute('data-theme', savedTheme);

  themeToggleBtn.addEventListener('click', () => {
    const currentTheme = htmlDoc.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    htmlDoc.setAttribute('data-theme', newTheme);
    localStorage.setItem('mail_shield_theme', newTheme);
  });

  // --- NAVIGATION ---
  const switchNav = (activeBtn, activeView) => {
    [btnNavAnalyzer, btnNavBatch, btnNavMetrics].forEach(b => b.classList.remove('active'));
    [viewVerifier, viewBatch, viewMetrics].forEach(v => v.classList.remove('active'));
    
    activeBtn.classList.add('active');
    activeView.classList.add('active');
    
    if (activeView === viewMetrics) {
      fetchMetrics();
    }
  };

  btnNavAnalyzer.addEventListener('click', () => switchNav(btnNavAnalyzer, viewVerifier));
  btnNavBatch.addEventListener('click', () => switchNav(btnNavBatch, viewBatch));
  btnNavMetrics.addEventListener('click', () => switchNav(btnNavMetrics, viewMetrics));

  // --- COUNTERS & PRESET PILLS ---
  const updateCounters = () => {
    const text = messageInput.value;
    charCounter.textContent = `${text.length} characters`;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    wordCounter.textContent = `${words} words`;
  };

  messageInput.addEventListener('input', () => {
    updateCounters();
    
    // Live Typing Debounced Detection
    typingIndicator.classList.add('active');
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      typingIndicator.classList.remove('active');
      if (messageInput.value.trim().length > 10) {
        performAnalysis(true); // silent background scan
      }
    }, 500);
  });

  document.querySelectorAll('.preset-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const type = pill.getAttribute('data-type');
      if (PRESETS[type]) {
        messageInput.value = PRESETS[type];
        updateCounters();
        performAnalysis(false);
      }
    });
  });

  btnPasteText.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      messageInput.value = text;
      updateCounters();
      if (text.trim()) performAnalysis(false);
    } catch (e) {
      alert('Clipboard permission denied or unsupported.');
    }
  });

  btnClearText.addEventListener('click', () => {
    messageInput.value = '';
    updateCounters();
    resultsPanel.classList.add('hidden');
  });

  // --- MAIN PREDICTION ANALYSIS ---
  const performAnalysis = async (isSilent = false) => {
    const text = messageInput.value.trim();
    if (!text) return;

    try {
      const resp = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (!resp.ok) return;
      const data = await resp.json();
      
      renderResults(data, text);
    } catch (err) {
      console.error('API Error:', err);
    }
  };

  btnAnalyze.addEventListener('click', () => performAnalysis(false));

  // --- RENDER RESULTS PANEL ---
  const renderResults = (data, rawText) => {
    resultsPanel.classList.remove('hidden');

    const isSpam = data.prediction === 'Spam';
    const score = data.spam_probability;

    // 1. Verdict Card
    verdictCard.className = `verdict-card ${isSpam ? 'danger' : 'success'}`;
    verdictTitle.textContent = isSpam ? `SPAM DETECTED (${data.risk_level.toUpperCase()})` : `LEGITIMATE EMAIL (HAM)`;
    verdictLabel.textContent = `ANALYSIS VERDICT • CONFIDENCE: ${data.confidence}%`;
    verdictDesc.textContent = isSpam
      ? "High statistical probability of malicious intent, unwanted solicitations, or phishing."
      : "This message exhibits normal communication patterns and safe formatting structure.";

    verdictIcon.innerHTML = isSpam
      ? `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
      : `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;

    // 2. Score Ring SVG
    scorePercent.textContent = `${score}%`;
    const circumference = 326.7;
    const offset = circumference - (score / 100) * circumference;
    scoreRing.style.strokeDashoffset = offset;

    // 3. Highlighted Text
    renderHighlights(rawText, data.triggers);

    // 4. Signal Gauges
    urgencyBar.style.width = `${data.signals.urgency_score}%`;
    urgencyVal.textContent = `${data.signals.urgency_score}%`;

    financialBar.style.width = `${data.signals.financial_score}%`;
    financialVal.textContent = `${data.signals.financial_score}%`;

    phishingBar.style.width = `${data.signals.phishing_score}%`;
    phishingVal.textContent = `${data.signals.phishing_score}%`;

    formattingBar.style.width = `${data.signals.formatting_anomaly_score}%`;
    formattingVal.textContent = `${data.signals.formatting_anomaly_score}%`;

    // 5. Models Consensus
    scoreLR.textContent = `${data.models.logistic_regression}%`;
    scoreNB.textContent = `${data.models.naive_bayes}%`;
    scoreRF.textContent = `${data.models.random_forest}%`;

    // 6. AI Rewrite / Spam Fixer
    origRewriteText.textContent = rawText;
    cleanRewriteText.textContent = data.ai_suggestion.clean_rewrite;
    rewriteAdvice.textContent = `AI Suggestion: ${data.ai_suggestion.advice}`;

    // Smooth scroll to results
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  // --- HIGHLIGHT RENDERER ---
  const renderHighlights = (text, triggers) => {
    triggerCountPill.textContent = `${triggers.length} Triggers Flagged`;
    if (!triggers || triggers.length === 0) {
      highlightedText.textContent = text;
      return;
    }

    // Build highlighted DOM string
    let html = '';
    let lastIdx = 0;

    triggers.forEach(tr => {
      if (tr.start >= lastIdx) {
        // text before trigger
        html += escapeHtml(text.substring(lastIdx, tr.start));
        // trigger mark
        const matchedStr = escapeHtml(text.substring(tr.start, tr.end));
        html += `<mark class="hl-trigger hl-${tr.category}" title="${tr.explanation}">${matchedStr}</mark>`;
        lastIdx = tr.end;
      }
    });

    if (lastIdx < text.length) {
      html += escapeHtml(text.substring(lastIdx));
    }

    highlightedText.innerHTML = html;
  };

  const escapeHtml = (str) => {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  };

  btnCopyCleanText.addEventListener('click', () => {
    navigator.clipboard.writeText(cleanRewriteText.textContent);
    btnCopyCleanText.textContent = 'Copied!';
    setTimeout(() => btnCopyCleanText.textContent = 'Copy Cleaned Version', 2000);
  });

  // --- BATCH SCANNER ---
  btnBrowseFile.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) processBatchFile(file);
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--accent-blue)';
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'var(--card-border)';
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--card-border)';
    if (e.dataTransfer.files.length) {
      processBatchFile(e.dataTransfer.files[0]);
    }
  });

  const processBatchFile = (file) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target.result;
      const lines = content.split(/\r?\n/).filter(line => line.trim().length > 5);
      
      try {
        const resp = await fetch('/api/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: lines })
        });
        
        const data = await resp.json();
        renderBatchResults(data.results);
      } catch (err) {
        alert('Batch processing failed. Check server logs.');
      }
    };
    reader.readAsText(file);
  };

  const renderBatchResults = (results) => {
    batchResultsWrapper.classList.remove('hidden');
    batchCount.textContent = results.length;
    batchTableBody.innerHTML = '';

    results.forEach(res => {
      const tr = document.createElement('tr');
      const isSpam = res.prediction === 'Spam';
      tr.innerHTML = `
        <td>${res.id}</td>
        <td>${escapeHtml(res.preview)}</td>
        <td><span class="${isSpam ? 'tag-spam' : 'tag-ham'}">${res.prediction}</span></td>
        <td><strong>${res.score}%</strong></td>
        <td>${isSpam ? '⚠️ High Risk' : '✅ Verified'}</td>
      `;
      batchTableBody.appendChild(tr);
    });
  };

  btnClearBatch.addEventListener('click', () => {
    batchResultsWrapper.classList.add('hidden');
    batchTableBody.innerHTML = '';
  });

  // --- METRICS FETCHING ---
  const fetchMetrics = async () => {
    try {
      const resp = await fetch('/api/metrics');
      if (!resp.ok) return;
      const data = await resp.json();

      if (data.logistic_regression) {
        metricAccLR.textContent = `${(data.logistic_regression.accuracy * 100).toFixed(1)}%`;
        metricAccNB.textContent = `${(data.naive_bayes.accuracy * 100).toFixed(1)}%`;
        metricAccRF.textContent = `${(data.random_forest.accuracy * 100).toFixed(1)}%`;
      }

      if (data.dataset) {
        statSpamCount.textContent = `${data.dataset.spam_count} (${((data.dataset.spam_count/data.dataset.total_emails)*100).toFixed(1)}%)`;
        statHamCount.textContent = `${data.dataset.ham_count} (${((data.dataset.ham_count/data.dataset.total_emails)*100).toFixed(1)}%)`;
      }

      if (data.top_spam_words) {
        topWordsCloud.innerHTML = '';
        data.top_spam_words.forEach(w => {
          const chip = document.createElement('div');
          chip.className = 'word-chip';
          chip.innerHTML = `${escapeHtml(w.word)} <span class="weight">+${w.weight}</span>`;
          topWordsCloud.appendChild(chip);
        });
      }
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
    }
  };
});
