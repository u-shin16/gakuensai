// animal_battle_stats.xlsx の基本ステータス。±10%は質問結果。素早さは変えない。
// 通常攻撃の威力は表にないので 1.0。会心は 5%。QTEあり。
// 鳥類のQTEは判定幅を1.5倍にしている（表には「広い」とだけある）。
const BASE_STATS = {
  ネコ科: { hp: 130, atk: 50, def: 28, spd: 80 },
  イヌ科: { hp: 200, atk: 50, def: 50, spd: 50 },
  大型: { hp: 240, atk: 40, def: 60, spd: 25 },
  鳥類: { hp: 210, atk: 65, def: 50, spd: 70 },
  爬虫類: { hp: 220, atk: 55, def: 68, spd: 45 },
};

const TRAITS = {
  ネコ科: "会心率+8%",
  イヌ科: "",
  大型: "先攻を取れない",
  鳥類: "QTE判定が広い",
  爬虫類: "毒などの状態異常",
};

const CRIT_MULT = 1.5;
const CAP = { up: 0.6, defUp: 1, down: 0.5, cut: 0.8, evasion: 0.6, crit: 1 };

const EXTRA = {
  吸収: { absorb: 0.3 },
  貫通: { pierce: true },
  ガード: { charges: [{ kind: "guard", value: 0.65 }] },
  気合: { buff: true, auras: [{ kind: "power", value: 0.45, rounds: 2 }] },
  硬化: { buff: true, auras: [{ kind: "defUp", value: 0.7, rounds: 3 }] },
  毒: { foeAuras: [{ kind: "poison", value: 0.2, rounds: 3 }] },
  弱体: { foeAuras: [{ kind: "atkDown", value: 0.2, rounds: 2 }] },
  反撃: { charges: [{ kind: "counter", value: 0.55 }] },
  身かわし: { charges: [{ kind: "guard", value: 0.8 }, { kind: "sureCrit", value: 1 }] },
  遠吠え: { buff: true, heal: 0.2, auras: [{ kind: "atkUp", value: 0.3, rounds: 2 }, { kind: "defUp", value: 0.5, rounds: 2 }] },
  根を張る: { buff: true, auras: [{ kind: "regen", value: 0.08, rounds: 3 }, { kind: "defUp", value: 0.4, rounds: 2 }] },
  追い風: { buff: true, auras: [{ kind: "evasion", value: 0.55, rounds: 1 }, { kind: "qteSlow", value: 1, rounds: 1 }] },
  封じ: { seal: true, foeAuras: [{ kind: "poison", value: 0.1, rounds: 3 }, { kind: "defDown", value: 0.15, rounds: 2 }] },
  初日の出: { buff: true, auras: [{ kind: "critUp", value: 0.45, rounds: 2 }], charges: [{ kind: "sureHit", value: 1 }] },
  雪化粧: { heal: 0.08, auras: [{ kind: "cut", value: 0.4, rounds: 2 }] },
  桜吹雪: { buff: true, auras: [{ kind: "critUp", value: 0.15, rounds: 2 }], foeAuras: [{ kind: "defDown", value: 0.25, rounds: 2 }] },
  春風: { buff: true, auras: [{ kind: "evasion", value: 0.45, rounds: 2 }, { kind: "qteSlow", value: 1, rounds: 1 }] },
  新緑: { buff: true, auras: [{ kind: "regen", value: 0.06, rounds: 3 }, { kind: "defUp", value: 0.3, rounds: 2 }] },
  梅雨: { auras: [{ kind: "evasion", value: 0.25, rounds: 2 }], foeAuras: [{ kind: "atkDown", value: 0.2, rounds: 2 }] },
  夏祭り: { buff: true, auras: [{ kind: "critUp", value: 0.15, rounds: 2 }], charges: [{ kind: "nextPower", value: 0.7 }] },
  入道雲: { buff: true, auras: [{ kind: "atkUp", value: 0.4, rounds: 2 }], charges: [{ kind: "sureHit", value: 1 }] },
  月見: { heal: 0.2, auras: [{ kind: "defUp", value: 0.3, rounds: 1 }] },
  紅葉: { foeAuras: [{ kind: "defDown", value: 0.15, rounds: 2 }, { kind: "atkDown", value: 0.1, rounds: 2 }] },
  木枯らし: { buff: true, auras: [{ kind: "critUp", value: 0.3, rounds: 2 }, { kind: "evasion", value: 0.25, rounds: 2 }] },
  冬至: { heal: 0.15, auras: [{ kind: "cut", value: 0.25, rounds: 2 }] },
};

function quizApi() {
  if (typeof window !== "undefined" && window.AnimalQuiz) return window.AnimalQuiz;
  return require("./quiz.js");
}

function blankAuras() {
  return {};
}

function skillFromName(name, tag) {
  const quiz = quizApi();
  const base = quiz.SKILLS[name];
  const extra = EXTRA[name] || {};
  if (base) {
    return {
      name,
      tag,
      power: base.power,
      hits: base.hits || 1,
      qte: !!base.qte,
      crit: base.crit || 0,
      miss: base.miss || 0,
      uses: base.uses,
      usesLeft: base.uses,
      absorb: extra.absorb || 0,
      pierce: !!extra.pierce,
      buff: !!extra.buff,
      heal: extra.heal || 0,
      auras: extra.auras || [],
      foeAuras: extra.foeAuras || [],
      charges: extra.charges || [],
      seal: !!extra.seal,
    };
  }
  const typeSkill = Object.values(quiz.TYPE_SKILLS).find((skill) => skill.name === name);
  const monthSkill = quiz.MONTH_SKILLS.find((skill) => skill.name === name);
  const info = typeSkill || monthSkill;
  return {
    name,
    tag,
    power: 0,
    hits: 1,
    qte: false,
    crit: 0,
    miss: 0,
    uses: info.uses,
    usesLeft: info.uses,
    absorb: extra.absorb || 0,
    pierce: false,
    buff: !!extra.buff,
    heal: extra.heal || 0,
    auras: extra.auras || [],
    foeAuras: extra.foeAuras || [],
    charges: extra.charges || [],
    seal: !!extra.seal,
  };
}

function normalAttack() {
  return {
    name: "通常攻撃",
    tag: "通常",
    power: 1,
    hits: 1,
    qte: true,
    crit: 0.05,
    miss: 0,
    uses: null,
    usesLeft: null,
    absorb: 0,
    pierce: false,
    buff: false,
    heal: 0,
    auras: [],
    foeAuras: [],
    charges: [],
    seal: false,
  };
}

function makeFighter(side, result, month) {
  const quiz = quizApi();
  const base = BASE_STATS[result.type];
  const hpMod = result.statUp === "HP" ? 1.1 : result.statDown === "HP" ? 0.9 : 1;
  const atkMod = result.statUp === "攻撃" ? 1.1 : result.statDown === "攻撃" ? 0.9 : 1;
  const defMod = result.statUp === "守備" ? 1.1 : result.statDown === "守備" ? 0.9 : 1;
  const typeSkill = quiz.TYPE_SKILLS[result.type];
  const monthSkill = quiz.MONTH_SKILLS[month - 1];
  return {
    side,
    type: result.type,
    month,
    maxHp: Math.round(base.hp * hpMod),
    hp: Math.round(base.hp * hpMod),
    atk: Math.round(base.atk * atkMod),
    def: Math.round(base.def * defMod),
    spd: base.spd,
    trait: TRAITS[result.type],
    auras: blankAuras(),
    charges: { guard: [], counter: [], sureHit: 0, sureCrit: 0, nextPower: 0 },
    seal: null,
    lastSkill: null,
    turns: 0,
    skills: [
      ...result.skills.map((name) => skillFromName(name, "質問")),
      skillFromName(typeSkill.name, "タイプ"),
      skillFromName(monthSkill.name, "誕生月"),
      normalAttack(),
    ],
  };
}

function auraList(fighter, kind) {
  return fighter.auras[kind] || [];
}

function auraSum(fighter, kind) {
  return auraList(fighter, kind).reduce((sum, entry) => sum + entry.value, 0);
}

function currentAtk(fighter) {
  const up = Math.min(CAP.up, auraSum(fighter, "atkUp"));
  const down = Math.min(CAP.down, auraSum(fighter, "atkDown"));
  return fighter.atk * (1 + up - down);
}

function currentDef(fighter) {
  const up = Math.min(CAP.defUp, auraSum(fighter, "defUp"));
  const down = Math.min(CAP.down, auraSum(fighter, "defDown"));
  return fighter.def * (1 + up - down);
}

const BUFF_KINDS = new Set(["atkUp", "defUp", "power", "critUp", "cut", "evasion", "regen", "qteSlow"]);

function putAura(fighter, source, spec, actor) {
  const list = fighter.auras[spec.kind] || (fighter.auras[spec.kind] = []);
  const entry = { source, value: spec.value, rounds: spec.rounds, fresh: BUFF_KINDS.has(spec.kind) };
  if (spec.kind === "poison") entry.dot = Math.max(1, Math.round(currentAtk(actor) * spec.value));
  const prev = list.find((item) => item.source === source);
  if (prev) {
    prev.rounds = spec.rounds;
    prev.fresh = entry.fresh;
    if (entry.dot) prev.dot = entry.dot;
  } else {
    list.push(entry);
  }
}

function putCharge(fighter, source, spec) {
  if (spec.kind === "guard" || spec.kind === "counter") {
    const list = fighter.charges[spec.kind];
    const prev = list.find((item) => item.source === source);
    if (prev) prev.value = spec.value;
    else list.push({ source, value: spec.value });
    return;
  }
  fighter.charges[spec.kind] = spec.value;
}

function canUse(fighter, skill) {
  if (skill.usesLeft === 0) return false;
  if (fighter.seal && fighter.seal.name === skill.name) return false;
  return true;
}

function buffActive(fighter, skill) {
  return skill.auras.some((spec) => auraList(fighter, spec.kind).some((entry) => entry.source === skill.name));
}

function attackScore(skill) {
  const miss = skill.qte ? 0 : skill.miss;
  const score = skill.power * skill.hits * (1 - miss) * (1 + skill.crit * 0.5);
  return skill.name === "通常攻撃" ? score - 10 : score;
}

function aiPick(fighter) {
  const usable = fighter.skills.filter((skill) => canUse(fighter, skill));
  const heal = usable.find((skill) => skill.heal >= 0.1 && fighter.hp < fighter.maxHp * 0.4);
  if (heal) return heal;
  const buff = usable.find((skill) => skill.buff && !buffActive(fighter, skill));
  if (buff && fighter.turns === 0) return buff;
  const attacks = usable.filter((skill) => skill.power);
  if (attacks.length) return attacks.slice().sort((a, b) => attackScore(b) - attackScore(a))[0];
  return usable[0] || null;
}

function applySupport(actor, target, skill, log) {
  if (!skill.power) log.push(`${actor.side}は${skill.name}を使った`);
  skill.auras.forEach((spec) => putAura(actor, skill.name, spec, actor));
  skill.foeAuras.forEach((spec) => putAura(target, skill.name, spec, actor));
  skill.charges.forEach((spec) => putCharge(actor, skill.name, spec));
  if (skill.heal) {
    const amount = Math.max(1, Math.round(actor.maxHp * skill.heal));
    actor.hp = Math.min(actor.maxHp, actor.hp + amount);
    log.push(`${actor.side}は ${amount} 回復した`);
  }
  if (skill.seal) {
    if (target.lastSkill && target.lastSkill !== "通常攻撃") {
      target.seal = { name: target.lastSkill };
      log.push(`${target.side}の${target.lastSkill}を封じた`);
    } else {
      log.push("封じる技がなかった");
    }
  }
}

function attackContext(actor, target, skill, qte) {
  const traitCrit = actor.type === "ネコ科" ? 0.08 : 0;
  return {
    sureHit: actor.charges.sureHit > 0,
    sureCrit: actor.charges.sureCrit > 0,
    evasion: Math.min(CAP.evasion, auraSum(target, "evasion")),
    powerAura: auraSum(actor, "power") + actor.charges.nextPower,
    critBonus: Math.min(CAP.crit, skill.crit + auraSum(actor, "critUp") + traitCrit),
    qte,
    dealt: 0,
  };
}

function landHit(actor, target, skill, ctx, rng, log) {
  if (!ctx.sureHit && !skill.qte && rng() < skill.miss) {
    log.push(`${skill.name}は外れた`);
    return { miss: true, damage: 0, crit: false, reduced: false };
  }
  let atk = currentAtk(actor);
  let def = currentDef(target);
  if (skill.pierce) def *= 0.5;
  const power = skill.power * (1 + ctx.powerAura);
  const crit = ctx.sureCrit || rng() < ctx.critBonus;
  const roll = 0.9 + rng() * 0.2;
  const raw = atk * power * (100 / (100 + def)) * ctx.qte * (crit ? CRIT_MULT : 1) * roll;
  const guard = actor === target ? 0 : Math.min(CAP.cut, target.charges.guard.reduce((sum, item) => sum + item.value, 0) + auraSum(target, "cut"));
  const damage = Math.max(1, Math.round(raw * (1 - guard)));
  target.hp -= damage;
  const reduced = guard > 0;
  log.push(`${target.side}に ${damage} ダメージ${crit ? "（会心）" : ""}${reduced ? "（軽減）" : ""}`);
  return { miss: false, damage, crit, reduced };
}

function applyAttackFollowup(actor, target, skill, dealt, log) {
  if (dealt > 0 && skill.absorb) {
    const heal = Math.max(1, Math.round(dealt * skill.absorb));
    actor.hp = Math.min(actor.maxHp, actor.hp + heal);
    log.push(`${actor.side}は ${heal} 吸収した`);
  }
  if (dealt > 0 && target.charges.counter.length) {
    const ratio = target.charges.counter.reduce((sum, item) => sum + item.value, 0);
    const back = Math.max(1, Math.round(dealt * ratio));
    actor.hp -= back;
    log.push(`${actor.side}に反撃 ${back}`);
  }
}

function closeAttack(actor, target, dealt) {
  actor.charges.sureHit = 0;
  actor.charges.sureCrit = 0;
  actor.charges.nextPower = 0;
  if (dealt > 0) {
    target.charges.guard = [];
    target.charges.counter = [];
  }
}

function resolveAttack(actor, target, skill, qte, rng, log) {
  const ctx = attackContext(actor, target, skill, qte);
  if (!ctx.sureHit && rng() < ctx.evasion) {
    log.push(`${target.side}は${skill.name}を回避した`);
  } else {
    for (let hit = 0; hit < skill.hits; hit += 1) {
      const blow = landHit(actor, target, skill, ctx, rng, log);
      ctx.dealt += blow.damage;
    }
    applyAttackFollowup(actor, target, skill, ctx.dealt, log);
  }
  closeAttack(actor, target, ctx.dealt);
}

function spendUse(skill) {
  if (skill.usesLeft != null) skill.usesLeft -= 1;
}

function skillToAct(actor, skill, log) {
  if (skill && canUse(actor, skill)) return skill;
  if (skill && actor.seal && actor.seal.name === skill.name) {
    log.push(`${actor.side}の${skill.name}は封じられていた`);
    const normal = actor.skills.find((item) => item.name === "通常攻撃" && canUse(actor, item));
    if (normal) return normal;
  }
  log.push(`${actor.side}は技を出せなかった`);
  return null;
}

async function playCombo(actor, target, skill, qte, log, view) {
  log.push(`${actor.side}の${skill.name}`);
  const ctx = attackContext(actor, target, skill, qte);
  const rng = Math.random;
  if (!ctx.sureHit && rng() < ctx.evasion) {
    log.push(`${target.side}は${skill.name}を回避した`);
    renderBattle(view({ phaseText: `${skill.name} 回避`, actor: actor.side, whiff: target.side }));
    await wait(520);
  } else {
    for (let hit = 0; hit < skill.hits; hit += 1) {
      const blow = landHit(actor, target, skill, ctx, rng, log);
      ctx.dealt += blow.damage;
      const key = target.side === "あなた" ? "player" : "enemy";
      renderBattle(view({
        phaseText: `${skill.name} ${hit + 1}/${skill.hits}`,
        actor: actor.side,
        whiff: blow.miss ? target.side : "",
        fxCrit: blow.crit ? { [key]: true } : {},
        fxCut: blow.reduced ? { [key]: true } : {},
      }));
      await wait(640);
    }
    const mark = log.length;
    applyAttackFollowup(actor, target, skill, ctx.dealt, log);
    if (log.length > mark) {
      renderBattle(view({
        phaseText: skill.name,
        actor: actor.side,
        fxCrit: fxCrit(log.slice(mark)),
      }));
      await wait(520);
    }
  }
  closeAttack(actor, target, ctx.dealt);
}

function finishAct(actor, target, skill, log) {
  applySupport(actor, target, skill, log);
  spendUse(skill);
  actor.lastSkill = skill.name;
  actor.turns += 1;
  if (actor.seal && actor.seal.name) actor.seal = null;
}

function act(actor, target, skill, qte, rng, log) {
  if (skill.power) {
    log.push(`${actor.side}の${skill.name}`);
    resolveAttack(actor, target, skill, qte, rng, log);
  }
  finishAct(actor, target, skill, log);
}

function endRound(player, enemy, log) {
  [player, enemy].forEach((fighter) => {
    auraList(fighter, "regen").forEach((entry) => {
      const amount = Math.max(1, Math.round(fighter.maxHp * entry.value));
      fighter.hp = Math.min(fighter.maxHp, fighter.hp + amount);
      log.push(`${fighter.side}は ${amount} 回復した`);
    });
  });
  [player, enemy].forEach((fighter) => {
    auraList(fighter, "poison").forEach((entry) => {
      fighter.hp -= entry.dot;
      log.push(`${fighter.side}は毒で ${entry.dot} ダメージ`);
    });
    Object.keys(fighter.auras).forEach((kind) => {
      fighter.auras[kind] = fighter.auras[kind].filter((entry) => {
        if (entry.fresh) {
          entry.fresh = false;
          return true;
        }
        entry.rounds -= 1;
        return entry.rounds > 0;
      });
    });
  });
}

function alive(fighter) {
  return fighter.hp > 0;
}

function turnOrder(a, b, rng) {
  if (a.type === "大型" && b.type !== "大型") return [b, a];
  if (b.type === "大型" && a.type !== "大型") return [a, b];
  if (a.spd === b.spd) return rng() < 0.5 ? [a, b] : [b, a];
  return a.spd > b.spd ? [a, b] : [b, a];
}

function simulateBattle(playerResult, playerMonth, enemyResult, enemyMonth, rng) {
  const random = rng || Math.random;
  const player = makeFighter("あなた", playerResult, playerMonth);
  const enemy = makeFighter("相手", enemyResult, enemyMonth);
  const log = [];
  let round = 1;
  while (alive(player) && alive(enemy)) {
    log.push(`-- ラウンド ${round}`);
    const chosen = {
      player: aiPick(player),
      enemy: aiPick(enemy),
    };
    const order = turnOrder(player, enemy, random);
    for (let i = 0; i < order.length; i += 1) {
      const actor = order[i];
      const target = actor === player ? enemy : player;
      if (!alive(actor) || !alive(target)) break;
      const skill = skillToAct(actor, actor === player ? chosen.player : chosen.enemy, log);
      if (skill) act(actor, target, skill, 1, random, log);
    }
    if (alive(player) && alive(enemy)) endRound(player, enemy, log);
    round += 1;
  }
  let winner = "draw";
  if (player.hp > 0 && enemy.hp <= 0) winner = "player";
  else if (enemy.hp > 0 && player.hp <= 0) winner = "enemy";
  else if (player.hp !== enemy.hp) winner = player.hp > enemy.hp ? "player" : "enemy";
  return { winner, rounds: round - 1, playerHp: player.hp, enemyHp: enemy.hp, log };
}

function skillBlurb(name) {
  const quiz = quizApi();
  const base = quiz.SKILLS[name];
  if (base) {
    const parts = [];
    if (base.power != null) parts.push(`威力${base.power}`);
    if (base.hits != null) parts.push(`${base.hits}ヒット`);
    if (base.qte != null) parts.push(base.qte ? "QTEあり" : "QTEなし");
    parts.push(`回数${base.uses}`);
    if (base.crit != null) parts.push(`会心${Math.round(base.crit * 1000) / 10}%`);
    if (base.miss != null) parts.push(`ミス${Math.round(base.miss * 1000) / 10}%`);
    return `${parts.join(" / ")}。${base.note}`;
  }
  const typed = Object.values(quiz.TYPE_SKILLS).find((skill) => skill.name === name);
  const month = quiz.MONTH_SKILLS.find((skill) => skill.name === name);
  const info = typed || month;
  if (info) return `回数${info.uses}。${info.main}／${info.sub}`;
  return "威力1 / 1ヒット / QTEあり / 回数無制限 / 会心5%。技封じの対象外。";
}

const Sfx = {
  ctx: null,
  ensure() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    if (!this.ctx) this.ctx = new AudioCtx();
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  },
  beep(freq, dur, type, gain, slide) {
    const ctx = this.ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(40, slide), now + dur);
    amp.gain.setValueAtTime(gain, now);
    amp.gain.exponentialRampToValueAtTime(0.001, now + dur);
    osc.connect(amp).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + dur + 0.02);
  },
  hit(crit) {
    if (crit) {
      this.beep(520, 0.1, "square", 0.05, 900);
      this.beep(760, 0.16, "triangle", 0.04);
    } else {
      this.beep(170, 0.09, "square", 0.045, 80);
    }
  },
  guard() {
    this.beep(310, 0.12, "triangle", 0.05, 180);
  },
  heal() {
    this.beep(480, 0.14, "sine", 0.045, 720);
  },
  select() {
    this.beep(340, 0.05, "sine", 0.03);
  },
  qte(label) {
    if (label === "PERFECT") this.beep(880, 0.16, "triangle", 0.05, 1320);
    else if (label === "成功") this.beep(560, 0.1, "sine", 0.04);
    else this.beep(150, 0.14, "sawtooth", 0.03, 70);
  },
  win() {
    this.beep(523, 0.1, "triangle", 0.045);
    setTimeout(() => this.beep(659, 0.1, "triangle", 0.045), 110);
    setTimeout(() => this.beep(784, 0.18, "triangle", 0.045), 220);
  },
  lose() {
    this.beep(240, 0.28, "sine", 0.045, 90);
  },
};

let shownHp = null;

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const STATUS_AURAS = [
  { id: "poison", glyph: "☠️", short: "毒", name: "毒", tone: "bad", detail: "ラウンドの終わりにダメージ" },
  { id: "atkDown", glyph: "⚔️", short: "攻−", name: "攻撃ダウン", tone: "down", detail: "攻撃が下がっている" },
  { id: "defDown", glyph: "🛡️", short: "守−", name: "守備ダウン", tone: "down", detail: "守備が下がっている" },
  { id: "qteSlow", glyph: "🐢", short: "遅い", name: "QTEが遅い", tone: "down", detail: "タイミングバーの動きが遅い" },
  { id: "atkUp", glyph: "⚔️", short: "攻+", name: "攻撃アップ", tone: "up", detail: "攻撃が上がっている" },
  { id: "defUp", glyph: "🛡️", short: "守+", name: "守備アップ", tone: "up", detail: "守備が上がっている" },
  { id: "power", glyph: "💥", short: "威力", name: "威力アップ", tone: "up", detail: "技の威力が上がっている" },
  { id: "critUp", glyph: "🎯", short: "会心", name: "会心アップ", tone: "up", detail: "会心が出やすくなっている" },
  { id: "cut", glyph: "🧱", short: "軽減", name: "ダメージ軽減", tone: "up", detail: "受けるダメージが減っている" },
  { id: "evasion", glyph: "💨", short: "回避", name: "回避", tone: "up", detail: "攻撃を確率で避ける" },
  { id: "regen", glyph: "💚", short: "回復", name: "持続回復", tone: "up", detail: "ラウンドの終わりに回復する" },
];

function statusItems(fighter) {
  const items = [];
  STATUS_AURAS.forEach((spec) => {
    const list = auraList(fighter, spec.id);
    if (!list.length) return;
    const rounds = list.reduce((max, entry) => Math.max(max, entry.rounds), 0);
    let detail = spec.detail;
    if (spec.id === "poison") {
      const dot = list.reduce((sum, entry) => sum + (entry.dot || 0), 0);
      detail = `ラウンドの終わりに ${dot} ダメージ`;
    }
    items.push({ ...spec, detail, rounds });
  });
  if (fighter.charges.guard.length) items.push({ id: "guard", glyph: "🛡️", short: "防", name: "ガード", tone: "up", detail: "次に受けるダメージを軽減する", rounds: null });
  if (fighter.charges.counter.length) items.push({ id: "counter", glyph: "↩️", short: "反撃", name: "反撃待ち", tone: "up", detail: "次に受けたダメージの一部を返す", rounds: null });
  if (fighter.charges.sureHit) items.push({ id: "sureHit", glyph: "🎯", short: "必中", name: "必中", tone: "up", detail: "次の攻撃は外れない", rounds: null });
  if (fighter.charges.sureCrit) items.push({ id: "sureCrit", glyph: "💥", short: "必心", name: "会心必中", tone: "up", detail: "次の攻撃は会心になる", rounds: null });
  if (fighter.charges.nextPower) items.push({ id: "nextPower", glyph: "⬆️", short: "次威", name: "次の威力アップ", tone: "up", detail: "次の攻撃の威力が上がる", rounds: null });
  if (fighter.seal) {
    items.push({
      id: "seal",
      glyph: "🚫",
      short: "封じ",
      name: `${fighter.seal.name}封じ`,
      tone: "bad",
      detail: `${fighter.seal.name}は出せない。通常攻撃は出せる`,
      rounds: null,
    });
  }
  const toneRank = { bad: 0, down: 1, up: 2 };
  items.sort((a, b) => toneRank[a.tone] - toneRank[b.tone]);
  return items;
}

function statusIcons(fighter, key) {
  const items = statusItems(fighter);
  if (!items.length) return "";
  return `<div class="icons">${items.map((item) => `
    <button type="button" class="badge ${item.tone}" data-badge="${key}:${item.id}" aria-label="${escapeHtml(item.name)}">
      <span class="glyph" aria-hidden="true">${item.glyph}</span>
      <span class="bname">${escapeHtml(item.short)}</span>
      ${item.rounds != null ? `<span class="bturn">${item.rounds}</span>` : ""}
    </button>`).join("")}</div>`;
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

const PORTRAITS = {
  ネコ科: "art/neko.png",
  イヌ科: "art/inu.png",
  大型: "art/oogata.png",
  鳥類: "art/tori.png",
  爬虫類: "art/hachuu.png",
};

function portraitHtml(type, extraClass) {
  const cls = extraClass ? ` ${extraClass}` : "";
  return `<div class="portrait${cls}"><img src="${PORTRAITS[type] || ""}" alt="" onerror="this.hidden=true"><span>イラスト<br>${escapeHtml(type)}</span></div>`;
}

function renderBattle(view) {
  const app = document.getElementById("app");
  const prev = shownHp || { player: view.player.hp, enemy: view.enemy.hp };
  const latest = view.log[view.log.length - 1] || "";
  const hud = (fighter, key) => {
    const from = Math.max(0, prev[key]) / fighter.maxHp;
    return `
      <section class="hud">
        <div class="hud-top">
          <h2>${escapeHtml(fighter.side)}・${escapeHtml(fighter.type)}</h2>
          <p>HP ${Math.max(0, fighter.hp)} / ${fighter.maxHp}</p>
        </div>
        <div class="hp ${fighter.hp / fighter.maxHp <= 0.3 ? "low" : ""}" id="hp-${key}"><span id="fill-${key}" style="width:${Math.max(0, Math.min(1, from)) * 100}%"></span></div>
        <div class="hud-top">
          <p class="trait">素早さ ${fighter.spd}${fighter.trait ? `／${escapeHtml(fighter.trait)}` : ""}</p>
          ${statusIcons(fighter, key)}
        </div>
      </section>`;
  };
  const skills = view.waiting
    ? `<div class="skill-grid">${view.player.skills.map((skill, index) => {
      const uses = skill.usesLeft == null ? "∞" : skill.usesLeft;
      return `<button class="choice" type="button" data-skill="${index}"><strong>${escapeHtml(skill.name)}</strong><span class="detail">${escapeHtml(skill.tag)} / 残り${uses}</span></button>`;
    }).join("")}</div>`
    : "";
  const qte = view.qte
    ? `<div class="qte ${view.player.type === "鳥類" ? "wide" : ""}" id="qte"><div class="good" style="${qteBandStyle(view.qteLayout, "good")}"></div><div class="perfect" style="${qteBandStyle(view.qteLayout, "perfect")}"></div><div class="marker" id="marker"></div></div><button class="primary" id="qte-stop" type="button">今だ！</button>`
    : "";
  const end = view.finished
    ? `<button class="primary" id="rematch" type="button">同じカードでもう一戦</button><button class="ghost" id="restart" type="button">診断からやり直す</button>`
    : "";
  const picks = view.picks
    ? `<section class="win"><h2>このラウンドの行動</h2><p>あなた　<strong>${escapeHtml(view.picks.player)}</strong></p><p>相手　<strong>${escapeHtml(view.picks.enemy)}</strong></p></section>`
    : "";
  app.innerHTML = `
    <div class="stage arena-stage${view.command ? " command" : ""}">
      <p class="phase">ラウンド ${view.round}　${escapeHtml(view.phaseText)}</p>
      ${hud(view.enemy, "enemy")}
      <div class="logline"><p>${escapeHtml(latest)}</p><button type="button" id="open-log">ログ</button></div>
      <div class="field">
        <div class="ground"></div>
        <div class="actor enemy" id="card-enemy">${portraitHtml(view.enemy.type, "field-art")}</div>
        <div class="actor player" id="card-player">${portraitHtml(view.player.type, "field-art")}</div>
      </div>
      ${hud(view.player, "player")}
      ${picks}
      <div class="dock">
        ${qte || skills}
        ${end}
      </div>
    </div>
    <div class="backdrop" id="backdrop" hidden></div>
    <div class="sheet" id="sheet" hidden></div>
  `;
  const openLog = document.getElementById("open-log");
  if (openLog) {
    openLog.onclick = () => {
      showSheet(`
        <h2>ログ</h2>
        <div class="log">${view.log.map((line) => `<p>${escapeHtml(line)}</p>`).join("")}</div>
        <button class="primary" data-close type="button">閉じる</button>
      `);
      const box = document.querySelector("#sheet .log");
      if (box) box.scrollTop = box.scrollHeight;
    };
  }
  document.querySelectorAll("[data-badge]").forEach((button) => {
    button.onclick = () => {
      const [key, id] = button.dataset.badge.split(":");
      const fighter = key === "player" ? view.player : view.enemy;
      const item = statusItems(fighter).find((entry) => entry.id === id);
      if (!item) return;
      showSheet(`
        <p class="badge-hero ${item.tone}">${item.glyph}</p>
        <h2>${escapeHtml(item.name)}</h2>
        <p>${escapeHtml(item.detail)}</p>
        <p>${item.rounds != null ? `残り ${item.rounds} ラウンド` : "次に発動する"}</p>
        <button class="primary" data-close type="button">閉じる</button>
      `);
    };
  });
  ["player", "enemy"].forEach((key) => {
    const fighter = key === "player" ? view.player : view.enemy;
    const fill = document.getElementById(`fill-${key}`);
    const from = Math.max(0, prev[key]) / fighter.maxHp;
    const to = Math.max(0, fighter.hp) / fighter.maxHp;
    fill.style.width = `${Math.max(0, Math.min(1, from)) * 100}%`;
    if (from !== to) {
      fill.getBoundingClientRect();
      fill.style.width = `${Math.max(0, Math.min(1, to)) * 100}%`;
    }
    const delta = fighter.hp - prev[key];
    if (delta === 0) return;
    const cardEl = document.getElementById(`card-${key}`);
    const crit = delta < 0 && (view.fxCrit || {})[key];
    const cut = delta < 0 && (view.fxCut || {})[key];
    cardEl.classList.add(delta < 0 ? "hurt" : "heal");
    const floater = document.createElement("div");
    floater.className = `floater ${delta < 0 ? (crit ? "crit" : "dmg") : "heal"}`;
    floater.textContent = `${delta < 0 ? "" : "+"}${delta}`;
    cardEl.appendChild(floater);
    if (crit) stampImpact(cardEl, "crit", "会心");
    if (cut) stampImpact(cardEl, crit ? "cut low" : "cut", "軽減");
    Sfx[delta < 0 ? "hit" : "heal"](crit);
    if (cut) Sfx.guard();
    if (delta < 0) {
      app.classList.remove("shake");
      app.getBoundingClientRect();
      app.classList.add("shake");
    }
  });
  if (view.whiff) {
    const cardEl = document.getElementById(view.whiff === "あなた" ? "card-player" : "card-enemy");
    if (cardEl) {
      const floater = document.createElement("div");
      floater.className = "floater miss";
      floater.textContent = "ミス";
      cardEl.appendChild(floater);
    }
  }
  if (view.actor) {
    const actorCard = document.getElementById(view.actor === "あなた" ? "card-player" : "card-enemy");
    if (actorCard) actorCard.classList.add("swing");
  }
  if (view.finished) {
    if (view.phaseText.includes("勝ち")) Sfx.win();
    else if (view.phaseText.includes("負け")) Sfx.lose();
  }
  shownHp = { player: view.player.hp, enemy: view.enemy.hp };
  const log = document.getElementById("log");
  if (log) log.scrollTop = log.scrollHeight;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function qteWindow(wide) {
  const perfectHalf = wide ? 0.075 : 0.05;
  const goodHalf = wide ? 0.225 : 0.15;
  const min = Math.max(0.3, goodHalf);
  const max = Math.min(0.7, 1 - goodHalf);
  return {
    center: min + Math.random() * (max - min),
    perfectHalf,
    goodHalf,
  };
}

function qteBandStyle(layout, band) {
  if (!layout) return "";
  const half = band === "perfect" ? layout.perfectHalf : layout.goodHalf;
  return `left:${(layout.center - half) * 100}%;width:${half * 200}%`;
}

function askQte(slow, layout) {
  return new Promise((resolve) => {
    const marker = document.getElementById("marker");
    const button = document.getElementById("qte-stop");
    const period = slow ? 2200 : 1200;
    const started = performance.now();
    let pos = 0;
    let stopped = false;
    function frame(now) {
      if (stopped) return;
      const cycle = ((now - started) / period) % 2;
      pos = cycle < 1 ? cycle : 2 - cycle;
      marker.style.left = `${pos * 100}%`;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    function finish() {
      if (stopped) return;
      stopped = true;
      document.removeEventListener("keydown", onKey);
      const dist = Math.abs(pos - layout.center);
      if (dist <= layout.perfectHalf) resolve({ mult: 1.5, label: "PERFECT" });
      else if (dist <= layout.goodHalf) resolve({ mult: 1, label: "成功" });
      else resolve({ mult: 0.5, label: "失敗" });
    }
    function onKey(event) {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        finish();
      }
    }
    button.onclick = finish;
    document.addEventListener("keydown", onKey);
  });
}

function fxCrit(lines) {
  return {
    player: lines.some((line) => line.includes("あなたに") && line.includes("会心")),
    enemy: lines.some((line) => line.includes("相手に") && line.includes("会心")),
  };
}

function fxCut(lines) {
  return {
    player: lines.some((line) => line.includes("あなたに") && line.includes("軽減")),
    enemy: lines.some((line) => line.includes("相手に") && line.includes("軽減")),
  };
}

function stampImpact(cardEl, kind, label) {
  const portrait = cardEl.querySelector(".portrait");
  if (!portrait) return;
  const stamp = document.createElement("div");
  stamp.className = `impact ${kind}`;
  stamp.textContent = label;
  portrait.appendChild(stamp);
}

async function playBattle(playerResult, playerMonth, enemyResult, enemyMonth) {
  const player = makeFighter("あなた", playerResult, playerMonth);
  const enemy = makeFighter("相手", enemyResult, enemyMonth);
  shownHp = null;
  Sfx.ensure();
  const log = [`相手は${enemy.type}（${enemy.month}月）`];
  let round = 1;
  let finished = false;

  function view(extra) {
    return {
      player,
      enemy,
      log: log.slice(),
      round,
      waiting: false,
      qte: false,
      finished,
      phaseText: "",
      ...extra,
    };
  }

  while (alive(player) && alive(enemy)) {
    renderBattle(view({ command: true, waiting: true, phaseText: "行動を選ぶ" }));
    const playerSkill = await new Promise((resolve) => {
      document.querySelectorAll("[data-skill]").forEach((button) => {
        button.onclick = () => {
          const picked = player.skills[Number(button.dataset.skill)];
          const usable = canUse(player, picked);
          const close = showSheet(`
            <h2>${escapeHtml(picked.name)}</h2>
            <p>${escapeHtml(skillBlurb(picked.name))}</p>
            ${usable ? `<button class="primary" id="use-skill" type="button">これに決める</button>` : `<p class="detail">今は使えない</p>`}
            <button class="ghost" data-close type="button">戻る</button>
          `);
          const use = document.getElementById("use-skill");
          if (use) {
            use.onclick = () => {
              close();
              resolve(picked);
            };
          }
        };
      });
    });
    const enemySkill = aiPick(enemy);
    Sfx.select();
    renderBattle(view({
      phaseText: "行動決定",
      picks: { player: playerSkill.name, enemy: enemySkill ? "決定" : "なし" },
    }));
    await wait(700);
    const order = turnOrder(player, enemy, Math.random);
    for (let i = 0; i < order.length; i += 1) {
      const actor = order[i];
      const target = actor === player ? enemy : player;
      if (!alive(actor) || !alive(target)) break;
      const planned = actor === player ? playerSkill : enemySkill;
      let skill = skillToAct(actor, planned, log);
      if (!skill) {
        renderBattle(view({ phaseText: `${actor.side}は動けなかった` }));
        await wait(700);
        continue;
      }
      let qte = 1;
      if (actor === player && skill.qte) {
        const qteLayout = qteWindow(player.type === "鳥類");
        renderBattle(view({ qte: true, qteLayout, phaseText: `${skill.name}：緑の帯で止める` }));
        const result = await askQte(auraSum(player, "qteSlow") > 0, qteLayout);
        qte = result.mult;
        Sfx.qte(result.label);
        const stop = document.getElementById("qte-stop");
        if (stop) stop.textContent = result.label;
        log.push(`QTE ${result.label}`);
        await wait(380);
      } else if (actor !== player) {
        renderBattle(view({ phaseText: "相手の行動" }));
        await wait(450);
      }
      if (skill.power && skill.hits > 1) {
        await playCombo(actor, target, skill, qte, log, view);
        finishAct(actor, target, skill, log);
      } else {
        const mark = log.length;
        act(actor, target, skill, qte, Math.random, log);
        renderBattle(view({
          phaseText: `${actor.side}の${skill.name}`,
          actor: actor.side,
          fxCrit: fxCrit(log.slice(mark)),
          fxCut: fxCut(log.slice(mark)),
        }));
        await wait(900);
      }
    }
    if (alive(player) && alive(enemy)) {
      const mark = log.length;
      endRound(player, enemy, log);
      round += 1;
      if (log.length > mark) {
        renderBattle(view({ phaseText: "ラウンドの終わり", fxCrit: fxCrit(log.slice(mark)) }));
        await wait(700);
      }
    } else break;
  }

  finished = true;
  let phaseText = "引き分け";
  if (player.hp > 0 && enemy.hp <= 0) phaseText = "勝ち";
  else if (enemy.hp > 0 && player.hp <= 0) phaseText = "負け";
  player.hp = Math.max(0, player.hp);
  enemy.hp = Math.max(0, enemy.hp);
  shownHp = { player: player.hp, enemy: enemy.hp };
  renderBattle(view({ phaseText, finished: true }));
  document.getElementById("rematch").onclick = () => playBattle(playerResult, playerMonth, enemyResult, enemyMonth);
  document.getElementById("restart").onclick = () => window.location.reload();
}

function start(result, month) {
  const quiz = quizApi();
  const enemyAnswers = Array.from({ length: 6 }, () => Math.floor(Math.random() * 4));
  const enemyMonth = 1 + Math.floor(Math.random() * 12);
  playBattle(result, month, quiz.judge(enemyAnswers), enemyMonth);
}

const AnimalBattle = { BASE_STATS, makeFighter, simulateBattle, start };
if (typeof window !== "undefined") window.AnimalBattle = AnimalBattle;
if (typeof module !== "undefined" && module.exports) module.exports = AnimalBattle;
