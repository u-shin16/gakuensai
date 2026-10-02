// 質問と点数は animal_battle_quiz.xlsx「質問と点数」と同じ。
// 同点は回答番号の合計 S（A=0 … D=3）で優先順位をずらす。乱数は使わない。
// 優先順はシートの並び。全4096通りの偏りと一致する。

const TYPE_ORDER = ["ネコ科", "イヌ科", "大型", "鳥類", "爬虫類"];
const STAT_ORDER = ["攻撃", "守備", "HP"];
const ATTACK_SKILLS = ["強打", "連撃", "急所狙い", "吸収", "貫通"];
const SKILL_ORDER = [
  "強打",
  "連撃",
  "急所狙い",
  "吸収",
  "貫通",
  "ガード",
  "気合",
  "硬化",
  "毒",
  "弱体",
  "反撃",
];

const QUESTIONS = [
  {
    id: "Q1",
    prompt: "宝箱を見つけた！どうする？",
    options: [
      { label: "すぐに開ける", type2: "ネコ科", type1: "イヌ科", stat: "攻撃", attack: "急所狙い", support: "気合" },
      { label: "罠を調べてから開ける", type2: "鳥類", type1: "爬虫類", stat: "守備", attack: "貫通", support: "ガード" },
      { label: "仲間と相談して開ける", type2: "イヌ科", type1: "大型", stat: "HP", attack: "吸収", support: "硬化" },
      { label: "見張りを立てて様子見", type2: "大型", type1: "鳥類", stat: "守備", attack: "強打", support: "反撃" },
    ],
  },
  {
    id: "Q2",
    prompt: "ライバルに勝負を挑まれた！",
    options: [
      { label: "受けて立つ", type2: "ネコ科", type1: "大型", stat: "攻撃", attack: "強打", support: "気合" },
      { label: "作戦を練ってから", type2: "爬虫類", type1: "鳥類", stat: "攻撃", attack: "連撃", support: "反撃" },
      { label: "ルールを確認する", type2: "鳥類", type1: "イヌ科", stat: "守備", attack: "貫通", support: "弱体" },
      { label: "みんなの動きを見て合わせる", type2: "イヌ科", type1: "大型", stat: "守備", attack: "吸収", support: "硬化" },
    ],
  },
  {
    id: "Q3",
    prompt: "長い道のりを行くなら？",
    options: [
      { label: "全力で駆け抜ける", type2: "ネコ科", type1: "鳥類", stat: "攻撃", attack: "連撃", support: "気合" },
      { label: "ペースを守って進む", type2: "イヌ科", type1: "大型", stat: "HP", attack: "吸収", support: "ガード" },
      { label: "近道や裏道を探す", type2: "爬虫類", type1: "ネコ科", stat: "守備", attack: "急所狙い", support: "毒" },
      { label: "重い荷物も背負って行く", type2: "大型", type1: "イヌ科", stat: "守備", attack: "強打", support: "硬化" },
    ],
  },
  {
    id: "Q4",
    prompt: "みんなで鍋を囲む。あなたは？",
    options: [
      { label: "具材を取り合う", type2: "ネコ科", type1: "爬虫類", stat: "攻撃", attack: "急所狙い", support: "弱体" },
      { label: "みんなに取り分ける", type2: "イヌ科", type1: "大型", stat: "HP", attack: "吸収", support: "反撃" },
      { label: "こっそり好物を確保", type2: "爬虫類", type1: "鳥類", stat: "守備", attack: "連撃", support: "毒" },
      { label: "全体を見て火加減を調整", type2: "鳥類", type1: "イヌ科", stat: "HP", attack: "貫通", support: "弱体" },
    ],
  },
  {
    id: "Q5",
    prompt: "苦手な相手が現れたら？",
    options: [
      { label: "正面からぶつかる", type2: "大型", type1: "ネコ科", stat: "攻撃", attack: "強打", support: "反撃" },
      { label: "距離をとって観察", type2: "鳥類", type1: "爬虫類", stat: "HP", attack: "貫通", support: "弱体" },
      { label: "軽くかわして逃げる", type2: "ネコ科", type1: "鳥類", stat: "HP", attack: "急所狙い", support: "ガード" },
      { label: "弱点を探って仕掛ける", type2: "爬虫類", type1: "イヌ科", stat: "攻撃", attack: "連撃", support: "毒" },
    ],
  },
  {
    id: "Q6",
    prompt: "理想の勝ち方は？",
    options: [
      { label: "一撃で決める", type2: "大型", type1: "ネコ科", stat: "攻撃", attack: "急所狙い", support: "気合" },
      { label: "じわじわ追い詰める", type2: "爬虫類", type1: "大型", stat: "HP", attack: "連撃", support: "毒" },
      { label: "無傷で勝つ", type2: "鳥類", type1: "ネコ科", stat: "守備", attack: "貫通", support: "ガード" },
      { label: "最後まで立っていた者が勝ち", type2: "イヌ科", type1: "大型", stat: "HP", attack: "吸収", support: "硬化" },
    ],
  },
];

function empty(keys) {
  const scores = {};
  keys.forEach((key) => {
    scores[key] = 0;
  });
  return scores;
}

function rotate(order, shift) {
  const amount = shift % order.length;
  return order.slice(amount).concat(order.slice(0, amount));
}

function pickByScore(scores, order, shift, mode) {
  const rotated = rotate(order, shift);
  let target = scores[order[0]];
  order.forEach((key) => {
    const value = scores[key];
    if (mode === "max" ? value > target : value < target) target = value;
  });
  return rotated.find((key) => scores[key] === target);
}

function pickTop(scores, order, shift, count) {
  const rank = new Map(rotate(order, shift).map((key, index) => [key, index]));
  return order
    .slice()
    .sort((a, b) => {
      if (scores[b] !== scores[a]) return scores[b] - scores[a];
      return rank.get(a) - rank.get(b);
    })
    .slice(0, count);
}

function judge(answers) {
  if (!Array.isArray(answers) || answers.length !== QUESTIONS.length) {
    throw new Error("回答は6問ぶん必要です");
  }
  const shift = answers.reduce((sum, index) => sum + index, 0);
  const types = empty(TYPE_ORDER);
  const stats = empty(STAT_ORDER);
  const skills = empty(SKILL_ORDER);

  answers.forEach((choice, questionIndex) => {
    const option = QUESTIONS[questionIndex].options[choice];
    if (!option) throw new Error("選択肢が不正です");
    types[option.type2] += 2;
    types[option.type1] += 1;
    stats[option.stat] += 1;
    skills[option.attack] += 1;
    skills[option.support] += 1;
  });

  const type = pickByScore(types, TYPE_ORDER, shift, "max");
  const statUp = pickByScore(stats, STAT_ORDER, shift, "max");
  const statRest = STAT_ORDER.filter((key) => key !== statUp);
  const statDown = rotate(STAT_ORDER, shift).find((key) => {
    if (!statRest.includes(key)) return false;
    return statRest.every((other) => stats[key] <= stats[other]);
  });
  const attack = pickByScore(skills, ATTACK_SKILLS, shift, "max");
  const pool = SKILL_ORDER.filter((key) => key !== attack);
  const others = pickTop(skills, pool, shift, 2);

  return {
    type,
    statUp,
    statDown,
    statFlat: STAT_ORDER.find((key) => key !== statUp && key !== statDown),
    attack,
    others,
    skills: [attack, ...others],
    scores: { types, stats, skills },
    shift,
  };
}

// animal_battle_skills.xlsx「質問由来11型」「タイプ専用5技」の数値。
const SKILLS = {
  強打: { power: 1.2, hits: 1, qte: true, uses: 2, crit: 0.1, miss: 0, note: "QTEで0.6〜1.8倍" },
  連撃: { power: 0.35, hits: 3, qte: false, uses: 4, crit: 0.05, miss: 0.1, note: "3回ヒット。ミス率はヒットごと" },
  急所狙い: { power: 0.9, hits: 1, qte: false, uses: 3, crit: 0.4, miss: 0.25, note: "ハイリスク型" },
  吸収: { power: 0.8, hits: 1, qte: false, uses: 3, crit: 0.1, miss: 0.1, note: "与ダメージの3割を回復" },
  貫通: { power: 0.9, hits: 1, qte: false, uses: 3, crit: 0.1, miss: 0.1, note: "相手の守備を半分無視して計算" },
  ガード: { uses: 2, note: "次に受けるダメージを50%軽減" },
  気合: { uses: 2, note: "2ターン、威力+30%" },
  硬化: { uses: 2, note: "3ターン、守備+30%" },
  毒: { uses: 3, note: "3ターン継続ダメージ（攻撃×0.2/ターン）" },
  弱体: { uses: 3, note: "2ターン、相手の攻撃−20%" },
  反撃: { uses: 2, note: "次に受けるダメージの40%を相手に返す" },
};

const TYPE_SKILLS = {
  ネコ科: {
    name: "身かわし",
    uses: 1,
    main: "次に受けるダメージを70%軽減",
    sub: "次の自分の攻撃が会心必中",
  },
  イヌ科: {
    name: "遠吠え",
    uses: 2,
    main: "2ラウンド、攻撃・守備を各+20%",
    sub: "最大HPの15%を回復",
  },
  大型: {
    name: "根を張る",
    uses: 1,
    main: "持続回復3ラウンド（最大HPの5%/ラウンド）",
    sub: "2ラウンド、守備+15%",
  },
  鳥類: {
    name: "追い風",
    uses: 2,
    main: "1ラウンド、回避40%（相手の攻撃が確率で外れる）",
    sub: "1ラウンド、QTEバーが遅くなる",
  },
  爬虫類: {
    name: "封じ",
    uses: 1,
    main: "相手が最後に使った技を1ラウンド封じる（通常攻撃は封じない）",
    sub: "毒3ラウンド（攻撃×0.1/ラウンド）＋守備−15%（2ラウンド）",
  },
};

const MONTH_SKILLS = [
  { name: "初日の出", uses: 2, main: "2ラウンド、会心率+30%", sub: "次の攻撃が必中" },
  { name: "雪化粧", uses: 2, main: "2ラウンド、被ダメージ25%軽減", sub: "最大HPの5%回復" },
  { name: "桜吹雪", uses: 2, main: "2ラウンド、相手の守備−25%", sub: "2ラウンド、会心率+10%" },
  { name: "春風", uses: 2, main: "2ラウンド、回避30%", sub: "1ラウンド、QTEバーが遅くなる" },
  { name: "新緑", uses: 1, main: "持続回復3ラウンド（最大HPの4%/ラウンド）", sub: "2ラウンド、守備+10%" },
  { name: "梅雨", uses: 2, main: "2ラウンド、相手の攻撃−20%", sub: "2ラウンド、回避15%" },
  { name: "夏祭り", uses: 1, main: "次の攻撃の威力+50%", sub: "2ラウンド、会心率+10%" },
  { name: "入道雲", uses: 2, main: "2ラウンド、攻撃+25%", sub: "次の攻撃が必中" },
  { name: "月見", uses: 1, main: "最大HPの15%回復", sub: "1ラウンド、守備+10%" },
  { name: "紅葉", uses: 2, main: "2ラウンド、相手の守備−15%", sub: "2ラウンド、相手の攻撃−10%" },
  { name: "木枯らし", uses: 2, main: "2ラウンド、会心率+20%", sub: "2ラウンド、回避15%" },
  { name: "冬至", uses: 1, main: "最大HPの10%回復", sub: "2ラウンド、被ダメージ15%軽減" },
];

function percent(value) {
  const shown = Math.round(value * 1000) / 10;
  return `${shown}%`;
}

function skillSpec(name) {
  const skill = SKILLS[name];
  const parts = [];
  if (skill.power != null) parts.push(`威力${skill.power}`);
  if (skill.hits != null) parts.push(`${skill.hits}ヒット`);
  if (skill.qte != null) parts.push(skill.qte ? "QTEあり" : "QTEなし");
  parts.push(`回数${skill.uses}`);
  if (skill.crit != null) parts.push(`会心${percent(skill.crit)}`);
  if (skill.miss != null) parts.push(`ミス${percent(skill.miss)}`);
  return `${parts.join(" / ")}。${skill.note}`;
}

const AnimalQuiz = {
  QUESTIONS,
  TYPE_ORDER,
  STAT_ORDER,
  ATTACK_SKILLS,
  SKILL_ORDER,
  SKILLS,
  TYPE_SKILLS,
  MONTH_SKILLS,
  judge,
};

if (typeof window !== "undefined") window.AnimalQuiz = AnimalQuiz;
if (typeof module !== "undefined" && module.exports) module.exports = AnimalQuiz;

if (typeof document !== "undefined") {
  const MARKS = ["A", "B", "C", "D"];
  const state = { phase: "month", month: 1, step: 0, answers: [] };

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function skillButton(slot, name) {
    return `<button class="choice" type="button" data-skill-name="${escapeHtml(name)}" data-skill-slot="${escapeHtml(slot)}"><strong>${escapeHtml(name)}</strong><span class="detail">${escapeHtml(slot)}</span></button>`;
  }

  function showSheet(html) {
    const backdrop = document.getElementById("backdrop");
    const sheet = document.getElementById("sheet");
    backdrop.hidden = false;
    sheet.hidden = false;
    sheet.innerHTML = html;
    const close = () => {
      backdrop.hidden = true;
      sheet.hidden = true;
      sheet.innerHTML = "";
    };
    backdrop.onclick = close;
    const closer = sheet.querySelector("[data-close]");
    if (closer) closer.onclick = close;
    return close;
  }

  function resultHtml(result) {
    const statLine = STAT_ORDER.map((stat) => {
      if (stat === result.statUp) return `<span class="up">${stat} +10%</span>`;
      if (stat === result.statDown) return `<span class="down">${stat} −10%</span>`;
      return `${stat} 変化なし`;
    }).join("<br>");
    const typeSkill = TYPE_SKILLS[result.type];
    const monthSkill = MONTH_SKILLS[state.month - 1];
    const skills = [
      skillButton("攻撃枠", result.attack),
      ...result.others.map((skill) => skillButton("技", skill)),
      skillButton("タイプ", typeSkill.name),
      skillButton(`${state.month}月`, monthSkill.name),
    ].join("");
    return `
      <div class="stage">
        <section class="win">
          <h2>診断結果</h2>
          <p class="type">${escapeHtml(result.type)}</p>
          <p>${statLine}</p>
        </section>
        <section class="win">
          <h2>技（タップで詳細）</h2>
          ${skills}
        </section>
        <div class="dock">
          <button class="primary" id="fight" type="button">このデータで戦う</button>
          <button class="ghost" id="again" type="button">診断をやり直す</button>
        </div>
      </div>
      <div class="backdrop" id="backdrop" hidden></div>
      <div class="sheet" id="sheet" hidden></div>
    `;
  }

  function renderMonth() {
    const app = document.getElementById("app");
    app.innerHTML = `
      <h1>動物バトル診断</h1>
      <p class="lead">誕生月の技は質問と関係なく、月だけで決まります。</p>
      <p class="prompt">誕生月は？</p>
      <div class="months" id="months"></div>
    `;
    const months = document.getElementById("months");
    MONTH_SKILLS.forEach((skill, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      button.textContent = `${index + 1}月`;
      button.onclick = () => {
        state.month = index + 1;
        state.phase = "quiz";
        state.step = 0;
        state.answers = [];
        render();
      };
      months.appendChild(button);
    });
  }

  function render() {
    const app = document.getElementById("app");
    if (!app) return;
    if (state.phase === "month") {
      renderMonth();
      return;
    }
    if (state.step >= QUESTIONS.length) {
      app.innerHTML = resultHtml(judge(state.answers));
      document.getElementById("again").onclick = () => {
        state.phase = "month";
        state.step = 0;
        state.answers = [];
        render();
      };
      document.getElementById("fight").onclick = () => {
        window.AnimalBattle.start(judge(state.answers), state.month);
      };
      document.querySelectorAll("[data-skill-name]").forEach((button) => {
        button.onclick = () => {
          const name = button.dataset.skillName;
          const typed = TYPE_SKILLS[judge(state.answers).type];
          const monthSkill = MONTH_SKILLS[state.month - 1];
          let body = `回数${monthSkill.uses}。${monthSkill.main}／${monthSkill.sub}`;
          if (typed && typed.name === name) body = `回数${typed.uses}。${typed.main}／${typed.sub}`;
          else if (monthSkill.name !== name) body = skillSpec(name);
          showSheet(`
            <h2>${escapeHtml(name)}</h2>
            <p>${escapeHtml(body)}</p>
            <button class="primary" data-close type="button">閉じる</button>
          `);
        };
      });
      return;
    }
    const question = QUESTIONS[state.step];
    app.innerHTML = `
      <h1>動物バトル診断</h1>
      <p class="lead">6問、だいたい1分。同じ答えなら、いつも同じ結果になります。</p>
      <p class="progress">${state.step + 1} / ${QUESTIONS.length}</p>
      <p class="prompt">${escapeHtml(question.prompt)}</p>
      <div id="choices"></div>
      <button class="ghost" id="back" type="button">戻る</button>
    `;
    const choices = document.getElementById("choices");
    question.options.forEach((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      button.innerHTML = `<strong><span class="mark">${MARKS[index]}</span>${escapeHtml(option.label)}</strong>`;
      button.onclick = () => {
        state.answers[state.step] = index;
        state.step += 1;
        render();
      };
      choices.appendChild(button);
    });
    document.getElementById("back").onclick = () => {
      if (state.step === 0) {
        state.phase = "month";
      } else {
        state.step -= 1;
      }
      render();
    };
  }

  render();
}
