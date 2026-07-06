const state = {
  unit: 1,
  words: [],
  currentIndex: 0,
  meaningVisible: false,
  draft: null,
  mode: "study",
};

const els = {
  unitList: document.querySelector("#unit-list"),
  wordList: document.querySelector("#word-list"),
  cardUnit: document.querySelector("#card-unit"),
  cardWord: document.querySelector("#card-word"),
  cardPhonetic: document.querySelector("#card-phonetic"),
  cardMeaning: document.querySelector("#card-meaning"),
  cardExample: document.querySelector("#card-example"),
  statTotal: document.querySelector("#stat-total"),
  statKnown: document.querySelector("#stat-known"),
  statReview: document.querySelector("#stat-review"),
  lookupForm: document.querySelector("#lookup-form"),
  saveForm: document.querySelector("#save-form"),
  wordInput: document.querySelector("#word-input"),
  editWord: document.querySelector("#edit-word"),
  editPhonetic: document.querySelector("#edit-phonetic"),
  editPos: document.querySelector("#edit-pos"),
  editMeaning: document.querySelector("#edit-meaning"),
  editExample: document.querySelector("#edit-example"),
  editSource: document.querySelector("#edit-source"),
  searchInput: document.querySelector("#search-input"),
  importInput: document.querySelector("#import-input"),
  message: document.querySelector("#message"),
  toggleMeaning: document.querySelector("#toggle-meaning"),
  knownButton: document.querySelector("#known-button"),
  reviewButton: document.querySelector("#review-button"),
  nextButton: document.querySelector("#next-button"),
  studyCard: document.querySelector(".study-card"),
  modeStudy: document.querySelector("#mode-study"),
  modeQuiz: document.querySelector("#mode-quiz"),
  quizPanel: document.querySelector("#quiz-panel"),
  quizWord: document.querySelector("#quiz-word"),
  quizPrompt: document.querySelector("#quiz-prompt"),
  quizForm: document.querySelector("#quiz-form"),
  quizAnswer: document.querySelector("#quiz-answer"),
  quizSubmit: document.querySelector("#quiz-submit"),
  quizFeedback: document.querySelector("#quiz-feedback"),
  quizReveal: document.querySelector("#quiz-reveal"),
  quizNext: document.querySelector("#quiz-next"),
};

function setMessage(text) {
  els.message.textContent = text;
}

async function api(path, options = {}) {
  const requestOptions = { ...options };
  const isFormData = requestOptions.body instanceof FormData;
  if (!isFormData) {
    requestOptions.headers = {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {}),
    };
  }

  const response = await fetch(path, requestOptions);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function buildText(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  node.textContent = text;
  return node;
}

function renderUnits() {
  els.unitList.textContent = "";
  for (let unit = 1; unit <= 20; unit += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `unit-button${unit === state.unit ? " active" : ""}`;
    button.textContent = `Unit ${unit}`;
    button.setAttribute("aria-pressed", String(unit === state.unit));
    button.addEventListener("click", () => {
      state.unit = unit;
      state.currentIndex = 0;
      state.meaningVisible = false;
      state.draft = null;
      els.saveForm.classList.add("hidden");
      renderUnits();
      loadWords();
    });
    els.unitList.appendChild(button);
  }
}

function currentWord() {
  return state.words[state.currentIndex] || null;
}

function renderStats() {
  els.statTotal.textContent = state.words.length;
  els.statKnown.textContent = state.words.filter((word) => word.status === "known").length;
  els.statReview.textContent = state.words.filter((word) => word.status === "review_later").length;
}

function renderCard() {
  const word = currentWord();
  els.cardUnit.textContent = `Unit ${state.unit}`;
  els.cardMeaning.classList.toggle("hidden", !state.meaningVisible || !word);
  els.cardExample.classList.toggle("hidden", !state.meaningVisible || !word || !word.example);
  els.toggleMeaning.textContent = state.meaningVisible ? "Hide meaning" : "Show meaning";

  if (!word) {
    els.cardWord.textContent = "No words yet";
    els.cardPhonetic.textContent = "Add a word to start studying.";
    els.cardMeaning.textContent = "";
    els.cardExample.textContent = "";
    els.toggleMeaning.disabled = true;
    els.knownButton.disabled = true;
    els.reviewButton.disabled = true;
    els.nextButton.disabled = true;
    return;
  }

  els.cardWord.textContent = word.word;
  els.cardPhonetic.textContent = [word.phonetic, word.part_of_speech].filter(Boolean).join(" / ");
  els.cardMeaning.textContent = word.chinese_meaning || "Chinese meaning needs manual entry.";
  els.cardExample.textContent = word.example || "";
  els.toggleMeaning.disabled = false;
  els.knownButton.disabled = false;
  els.reviewButton.disabled = false;
  els.nextButton.disabled = state.words.length <= 1;
}

function normalizeAnswer(text) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[；;，,。.\s]+/g, "");
}

function acceptedMeanings(word) {
  return (word.chinese_meaning || "")
    .split(/[；;，,、]/)
    .map((item) => normalizeAnswer(item))
    .filter(Boolean);
}

function resetQuiz() {
  els.quizAnswer.value = "";
  els.quizFeedback.textContent = "";
}

function renderMode() {
  const isQuiz = state.mode === "quiz";
  els.studyCard.classList.toggle("hidden", isQuiz);
  els.quizPanel.classList.toggle("hidden", !isQuiz);
  els.modeStudy.classList.toggle("active", !isQuiz);
  els.modeQuiz.classList.toggle("active", isQuiz);
  els.modeStudy.setAttribute("aria-pressed", String(!isQuiz));
  els.modeQuiz.setAttribute("aria-pressed", String(isQuiz));
}

function renderQuiz() {
  const word = currentWord();
  if (!word) {
    els.quizWord.textContent = "No words yet";
    els.quizPrompt.textContent = "Add a word before starting a quiz.";
    els.quizAnswer.disabled = true;
    els.quizSubmit.disabled = true;
    els.quizReveal.disabled = true;
    els.quizNext.disabled = true;
    return;
  }

  els.quizWord.textContent = word.word;
  els.quizPrompt.textContent = [word.phonetic, word.part_of_speech].filter(Boolean).join(" / ");
  if (!els.quizPrompt.textContent) {
    els.quizPrompt.textContent = "Type the Chinese meaning for the word.";
  }
  els.quizAnswer.disabled = false;
  els.quizSubmit.disabled = false;
  els.quizReveal.disabled = false;
  els.quizNext.disabled = state.words.length <= 1;
}

function makeActionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function renderWordList() {
  els.wordList.textContent = "";
  if (state.words.length === 0) {
    els.wordList.appendChild(buildText("p", "empty-copy", "No words in this unit yet."));
    return;
  }

  state.words.forEach((word, index) => {
    const row = document.createElement("div");
    row.className = "word-row";

    const text = document.createElement("div");
    text.appendChild(buildText("strong", "", word.word));
    text.appendChild(
      buildText(
        "span",
        "",
        `${word.part_of_speech || "unknown"} / ${word.chinese_meaning || "manual meaning needed"}`
      )
    );

    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.appendChild(
      makeActionButton("Study", () => {
        state.currentIndex = index;
        state.meaningVisible = false;
        resetQuiz();
        render();
      })
    );
    actions.appendChild(makeActionButton("Edit", () => fillEditForm(word)));
    actions.appendChild(makeActionButton("Delete", () => deleteWord(word)));

    row.append(text, actions);
    els.wordList.appendChild(row);
  });
}

function render() {
  renderMode();
  renderStats();
  renderCard();
  renderQuiz();
  renderWordList();
}

async function loadWords() {
  const query = els.searchInput.value.trim();
  const data = await api(`/api/words?unit=${state.unit}&q=${encodeURIComponent(query)}`);
  state.words = data.words;
  if (state.currentIndex >= state.words.length) {
    state.currentIndex = 0;
  }
  resetQuiz();
  render();
}

function fillEditForm(entry) {
  state.draft = entry.id ? entry : null;
  els.editWord.value = entry.word || "";
  els.editPhonetic.value = entry.phonetic || "";
  els.editPos.value = entry.part_of_speech || "";
  els.editMeaning.value = entry.chinese_meaning || "";
  els.editExample.value = entry.example || "";
  els.editSource.value = entry.source || "manual";
  els.saveForm.classList.remove("hidden");
}

async function lookupWord(event) {
  event.preventDefault();
  const word = els.wordInput.value.trim();
  if (!word) {
    setMessage("Please enter an English word.");
    return;
  }
  setMessage("Looking up word...");
  try {
    const data = await api("/api/lookup", {
      method: "POST",
      body: JSON.stringify({ word }),
    });
    fillEditForm(data.entry);
    setMessage(
      data.entry.source === "manual"
        ? "No dictionary result. Fill details manually."
        : "Dictionary result ready to review."
    );
  } catch (error) {
    setMessage(error.message);
  }
}

async function saveWord(event) {
  event.preventDefault();
  const editableFields = {
    phonetic: els.editPhonetic.value,
    part_of_speech: els.editPos.value,
    chinese_meaning: els.editMeaning.value,
    example: els.editExample.value,
    source: els.editSource.value || "manual",
  };

  try {
    if (state.draft && state.draft.id) {
      await api(`/api/words/${state.draft.id}`, {
        method: "PATCH",
        body: JSON.stringify(editableFields),
      });
      setMessage("Word updated.");
    } else {
      await api("/api/words", {
        method: "POST",
        body: JSON.stringify({
          unit: state.unit,
          word: els.editWord.value,
          ...editableFields,
        }),
      });
      setMessage("Word saved.");
    }
    els.saveForm.classList.add("hidden");
    els.lookupForm.reset();
    state.draft = null;
    await loadWords();
  } catch (error) {
    setMessage(error.message);
  }
}

async function updateStatus(status) {
  const word = currentWord();
  if (!word) {
    return;
  }
  try {
    await api(`/api/words/${word.id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    setMessage(status === "known" ? "Marked as known." : "Marked for review.");
    await loadWords();
  } catch (error) {
    setMessage(error.message);
  }
}

async function deleteWord(word) {
  const confirmed = window.confirm(`Delete "${word.word}" from Unit ${word.unit}?`);
  if (!confirmed) {
    return;
  }
  try {
    await api(`/api/words/${word.id}`, { method: "DELETE" });
    setMessage("Word deleted.");
    await loadWords();
  } catch (error) {
    setMessage(error.message);
  }
}

function switchMode(mode) {
  state.mode = mode;
  state.meaningVisible = false;
  resetQuiz();
  render();
  if (mode === "quiz" && currentWord()) {
    els.quizAnswer.focus();
  }
}

function submitQuiz(event) {
  event.preventDefault();
  const word = currentWord();
  if (!word) {
    return;
  }

  const answer = normalizeAnswer(els.quizAnswer.value);
  if (!answer) {
    els.quizFeedback.textContent = "请输入你的答案。";
    return;
  }

  const meanings = acceptedMeanings(word);
  const isCorrect = meanings.some(
    (meaning) => answer.includes(meaning) || meaning.includes(answer)
  );
  els.quizFeedback.textContent = isCorrect
    ? "答对了。"
    : `还不完全对：${word.chinese_meaning || "这个词还没有中文释义。"}`;
}

async function importCsv() {
  const file = els.importInput.files[0];
  if (!file) {
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  try {
    const report = await api("/api/import", {
      method: "POST",
      body: formData,
    });
    setMessage(`Imported ${report.imported}; skipped ${report.skipped}.`);
    await loadWords();
  } catch (error) {
    setMessage(error.message);
  } finally {
    els.importInput.value = "";
  }
}

let searchTimeout = null;

els.lookupForm.addEventListener("submit", lookupWord);
els.saveForm.addEventListener("submit", saveWord);
els.searchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimeout);
  searchTimeout = window.setTimeout(() => {
    state.currentIndex = 0;
    state.meaningVisible = false;
    resetQuiz();
    loadWords().catch((error) => setMessage(error.message));
  }, 160);
});
els.importInput.addEventListener("change", importCsv);
els.toggleMeaning.addEventListener("click", () => {
  state.meaningVisible = !state.meaningVisible;
  renderCard();
});
els.knownButton.addEventListener("click", () => updateStatus("known"));
els.reviewButton.addEventListener("click", () => updateStatus("review_later"));
els.nextButton.addEventListener("click", () => {
  if (state.words.length === 0) {
    return;
  }
  state.currentIndex = (state.currentIndex + 1) % state.words.length;
  state.meaningVisible = false;
  resetQuiz();
  render();
});
els.modeStudy.addEventListener("click", () => switchMode("study"));
els.modeQuiz.addEventListener("click", () => switchMode("quiz"));
els.quizForm.addEventListener("submit", submitQuiz);
els.quizReveal.addEventListener("click", () => {
  const word = currentWord();
  els.quizFeedback.textContent = word
    ? word.chinese_meaning || "这个词还没有中文释义。"
    : "";
});
els.quizNext.addEventListener("click", () => {
  if (state.words.length === 0) {
    return;
  }
  state.currentIndex = (state.currentIndex + 1) % state.words.length;
  state.meaningVisible = false;
  resetQuiz();
  render();
  els.quizAnswer.focus();
});

renderUnits();
loadWords().catch((error) => setMessage(error.message));
