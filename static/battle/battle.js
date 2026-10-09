// animal_battle_stats.xlsx の基本ステータス。±10%は質問結果。素早さは変えない。
// 通常攻撃の威力は表にないので 1.0。会心は 5%。QTEなし。
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
const CAP = { up: 0.6, defUp: 1, down: 0.65, cut: 0.9, evasion: 0.75, crit: 1, healDown: 0.75 };

const EXTRA = {
  吸収: { absorb: 0.3 },
  貫通: { pierce: true },
  ガード: { charges: [{ kind: "guard", value: 0.9 }] },
  気合: { buff: true, auras: [{ kind: "power", value: 0.45, rounds: 2 }] },
  硬化: { buff: true, auras: [{ kind: "defUp", value: 1, rounds: 3 }] },
  毒: { foeAuras: [{ kind: "poison", value: 0.45, rounds: 3 }] },
  弱体: { foeAuras: [{ kind: "atkDown", value: 0.6, rounds: 3 }] },
  反撃: { charges: [{ kind: "counter", value: 0.9 }] },
  身かわし: { charges: [{ kind: "guard", value: 0.8 }, { kind: "sureCrit", value: 1 }] },
  遠吠え: { buff: true, heal: 0.2, auras: [{ kind: "atkUp", value: 0.3, rounds: 2 }, { kind: "defUp", value: 0.9, rounds: 2 }] },
  根を張る: { buff: true, auras: [{ kind: "regen", value: 0.08, rounds: 3 }, { kind: "defUp", value: 0.85, rounds: 2 }] },
  追い風: { buff: true, auras: [{ kind: "evasion", value: 0.7, rounds: 2 }, { kind: "qteSlow", value: 1, rounds: 1 }] },
  封じ: { seal: true, foeAuras: [{ kind: "healDown", value: 0.6, rounds: 5 }, { kind: "defDown", value: 0.55, rounds: 3 }] },
  初日の出: { buff: true, auras: [{ kind: "critUp", value: 0.45, rounds: 2 }], charges: [{ kind: "sureHit", value: 1 }] },
  雪化粧: { heal: 0.08, auras: [{ kind: "cut", value: 0.75, rounds: 2 }] },
  桜吹雪: { buff: true, auras: [{ kind: "critUp", value: 0.15, rounds: 2 }], foeAuras: [{ kind: "defDown", value: 0.6, rounds: 2 }] },
  春風: { buff: true, auras: [{ kind: "evasion", value: 0.6, rounds: 2 }, { kind: "qteSlow", value: 1, rounds: 1 }] },
  新緑: { buff: true, auras: [{ kind: "regen", value: 0.06, rounds: 3 }, { kind: "defUp", value: 0.8, rounds: 2 }] },
  梅雨: { auras: [{ kind: "evasion", value: 0.6, rounds: 2 }], foeAuras: [{ kind: "atkDown", value: 0.55, rounds: 2 }] },
  夏祭り: { buff: true, auras: [{ kind: "critUp", value: 0.15, rounds: 2 }], charges: [{ kind: "nextPower", value: 0.7 }] },
  入道雲: { buff: true, auras: [{ kind: "atkUp", value: 0.4, rounds: 2 }], charges: [{ kind: "sureHit", value: 1 }] },
  月見: { heal: 0.2, auras: [{ kind: "defUp", value: 1, rounds: 1 }] },
  紅葉: { foeAuras: [{ kind: "defDown", value: 0.55, rounds: 2 }, { kind: "atkDown", value: 0.45, rounds: 2 }] },
  木枯らし: { buff: true, auras: [{ kind: "critUp", value: 0.3, rounds: 2 }, { kind: "evasion", value: 0.6, rounds: 2 }] },
  冬至: { heal: 0.15, auras: [{ kind: "cut", value: 0.7, rounds: 2 }] },
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
    qte: false,
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

function receiveHeal(fighter, raw) {
  const cut = Math.min(CAP.healDown, auraSum(fighter, "healDown"));
  return Math.max(0, Math.round(raw * (1 - cut)));
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

function effectLive(fighter, target, skill) {
  if (skill.auras.some((spec) => auraList(fighter, spec.kind).some((entry) => entry.source === skill.name))) return true;
  if (target && skill.foeAuras.some((spec) => auraList(target, spec.kind).some((entry) => entry.source === skill.name))) return true;
  if (skill.charges.some((spec) => {
    if (spec.kind === "guard" || spec.kind === "counter") {
      return fighter.charges[spec.kind].some((item) => item.source === skill.name);
    }
    return fighter.charges[spec.kind] > 0;
  })) return true;
  return !!(skill.seal && target && target.seal);
}

function aiPick(fighter, target) {
  const usable = fighter.skills.filter((skill) => canUse(fighter, skill));
  const heal = usable.find((skill) => skill.heal >= 0.08 && fighter.hp < fighter.maxHp * 0.5);
  if (heal) return heal;
  const support = usable.find((skill) => !skill.power && !effectLive(fighter, target, skill));
  if (support) return support;
  const attacks = usable.filter((skill) => skill.power);
  if (attacks.length) return attacks.slice().sort((a, b) => attackScore(b) - attackScore(a))[0];
  return usable[0] || null;
}

function attackScore(skill) {
  const miss = skill.qte ? 0 : skill.miss;
  const score = skill.power * skill.hits * (1 - miss) * (1 + skill.crit * 0.5);
  return skill.name === "通常攻撃" ? score - 10 : score;
}

const CHARGE_BUFFS = {
  guard: { id: "guard", glyph: "🛡️", short: "防", name: "ガード", tone: "up" },
  counter: { id: "counter", glyph: "↩️", short: "反撃", name: "反撃待ち", tone: "up" },
  sureHit: { id: "sureHit", glyph: "🎯", short: "必中", name: "必中", tone: "up" },
  sureCrit: { id: "sureCrit", glyph: "💥", short: "必会", name: "会心必中", tone: "up" },
  nextPower: { id: "nextPower", glyph: "⬆️", short: "次威", name: "次の威力アップ", tone: "up" },
};

function buffGrants(skill) {
  const items = [];
  skill.auras.forEach((spec) => {
    if (!BUFF_KINDS.has(spec.kind)) return;
    const item = STATUS_AURAS.find((entry) => entry.id === spec.kind);
    if (item) items.push(item);
  });
  skill.charges.forEach((spec) => {
    if (CHARGE_BUFFS[spec.kind]) items.push(CHARGE_BUFFS[spec.kind]);
  });
  return items;
}

function applySupport(actor, target, skill, log) {
  if (!skill.power) log.push(`${actor.side}は${skill.name}を使った`);
  skill.auras.forEach((spec) => putAura(actor, skill.name, spec, actor));
  skill.foeAuras.forEach((spec) => putAura(target, skill.name, spec, actor));
  skill.charges.forEach((spec) => putCharge(actor, skill.name, spec));
  buffGrants(skill).forEach((item) => log.push(`${actor.side}に ${item.name}`));
  if (skill.heal) {
    const raw = Math.max(1, Math.round(actor.maxHp * skill.heal));
    const amount = receiveHeal(actor, raw);
    if (amount > 0) {
      actor.hp = Math.min(actor.maxHp, actor.hp + amount);
      log.push(`${actor.side}は ${amount} 回復した`);
    } else {
      log.push(`${actor.side}は回復できなかった`);
    }
  }
  if (skill.seal) {
    if (target.lastSkill && target.lastSkill !== "通常攻撃") {
      target.seal = { name: target.lastSkill, rounds: 4 };
      log.push(`${target.side}の${target.lastSkill}を封じた`);
    } else {
      log.push("封じる技がなかった");
    }
  }
}

function attackContext(actor, target, skill, qte) {
  const traitCrit = actor.type === "ネコ科" ? 0.08 : 0;
  const perfectAim = skill.name === "急所狙い" && qte >= 1.5;
  return {
    sureHit: actor.charges.sureHit > 0 || perfectAim,
    sureCrit: actor.charges.sureCrit > 0,
    evasion: Math.min(CAP.evasion, auraSum(target, "evasion")),
    powerAura: auraSum(actor, "power"),
    nextPower: actor.charges.nextPower,
    critBonus: Math.min(CAP.crit, skill.crit + auraSum(actor, "critUp") + traitCrit),
    qte,
    dealt: 0,
  };
}

function landHit(actor, target, skill, ctx, rng, log, opening) {
  const sureHit = opening && ctx.sureHit;
  if (!sureHit && rng() < skill.miss) {
    log.push(`${skill.name}は外れた`);
    return { miss: true, damage: 0, crit: false, reduced: false };
  }
  let atk = currentAtk(actor);
  let def = currentDef(target);
  if (skill.pierce) def *= 0.5;
  const power = skill.power * (1 + ctx.powerAura + (opening ? ctx.nextPower : 0));
  const crit = (opening && ctx.sureCrit) || rng() < ctx.critBonus;
  const roll = 0.9 + rng() * 0.2;
  const raw = atk * power * (100 / (100 + def)) * ctx.qte * (crit ? CRIT_MULT : 1) * roll;
  const guardCharge = opening ? target.charges.guard.reduce((sum, item) => sum + item.value, 0) : 0;
  const guard = actor === target || (skill.pierce && ctx.qte >= 1.2)
    ? 0
    : Math.min(CAP.cut, guardCharge + auraSum(target, "cut"));
  const damage = Math.max(1, Math.round(raw * (1 - guard)));
  target.hp -= damage;
  const reduced = guard > 0;
  log.push(`${target.side}に ${damage} ダメージ${crit ? "（会心）" : ""}${reduced ? "（軽減）" : ""}`);
  return { miss: false, damage, crit, reduced };
}

function applyAttackFollowup(actor, target, skill, dealt, firstDamage, log) {
  if (dealt > 0 && skill.absorb) {
    const raw = Math.max(1, Math.round(dealt * skill.absorb));
    const heal = receiveHeal(actor, raw);
    if (heal > 0) {
      actor.hp = Math.min(actor.maxHp, actor.hp + heal);
      log.push(`${actor.side}は ${heal} 吸収した`);
    } else {
      log.push(`${actor.side}は吸収できなかった`);
    }
  }
  if (firstDamage > 0 && target.charges.counter.length) {
    const ratio = target.charges.counter.reduce((sum, item) => sum + item.value, 0);
    const back = Math.max(1, Math.round(firstDamage * ratio));
    actor.hp -= back;
    log.push(`${actor.side}に反撃 ${back}`);
  }
}

function closeAttack(actor, target, firstDamage) {
  actor.charges.sureHit = 0;
  actor.charges.sureCrit = 0;
  actor.charges.nextPower = 0;
  if (firstDamage > 0) {
    target.charges.guard = [];
    target.charges.counter = [];
  }
}

function resolveAttack(actor, target, skill, qte, rng, log) {
  const ctx = attackContext(actor, target, skill, qte);
  let firstDamage = 0;
  if (!ctx.sureHit && rng() < ctx.evasion) {
    log.push(`${target.side}は${skill.name}を回避した`);
  } else {
    for (let hit = 0; hit < skill.hits; hit += 1) {
      const blow = landHit(actor, target, skill, ctx, rng, log, hit === 0);
      if (hit === 0) firstDamage = blow.damage;
      ctx.dealt += blow.damage;
    }
    applyAttackFollowup(actor, target, skill, ctx.dealt, firstDamage, log);
  }
  closeAttack(actor, target, firstDamage);
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
  let firstDamage = 0;
  if (!ctx.sureHit && rng() < ctx.evasion) {
    log.push(`${target.side}は${skill.name}を回避した`);
    renderBattle(view({ banner: skill.name, bannerSide: sideOf(actor), phaseText: `${skill.name} 回避`, actor: actor.side, whiff: target.side, whiffKind: "evade" }));
    await wait(900);
  } else {
    for (let hit = 0; hit < skill.hits; hit += 1) {
      const blow = landHit(actor, target, skill, ctx, rng, log, hit === 0);
      if (hit === 0) firstDamage = blow.damage;
      ctx.dealt += blow.damage;
      const key = target.side === "あなた" ? "player" : "enemy";
      renderBattle(view({
        banner: skill.name,
        bannerSide: sideOf(actor),
        phaseText: `${skill.name} ${hit + 1}/${skill.hits}`,
        actor: actor.side,
        whiff: blow.miss ? target.side : "",
        fxCrit: blow.crit ? { [key]: true } : {},
        fxCut: blow.reduced ? { [key]: true } : {},
      }));
      await wait(1100);
    }
    const mark = log.length;
    applyAttackFollowup(actor, target, skill, ctx.dealt, firstDamage, log);
    if (log.length > mark) {
      renderBattle(view({
        banner: skill.name,
        bannerSide: sideOf(actor),
        phaseText: skill.name,
        actor: actor.side,
        fxCrit: fxCrit(log.slice(mark)),
      }));
      await wait(900);
    }
  }
  closeAttack(actor, target, firstDamage);
}

function finishAct(actor, target, skill, log) {
  applySupport(actor, target, skill, log);
  spendUse(skill);
  actor.lastSkill = skill.name;
  actor.turns += 1;
}

function act(actor, target, skill, qte, rng, log) {
  if (skill.power) {
    log.push(`${actor.side}の${skill.name}`);
    resolveAttack(actor, target, skill, qte, rng, log);
  }
  finishAct(actor, target, skill, log);
}

function rechargeQuestion(fighter, log, rng) {
  const skills = fighter.skills.filter((skill) => skill.tag === "質問");
  if (!skills.length || skills.some((skill) => skill.usesLeft > 0)) return;
  const skill = skills[Math.floor(rng() * skills.length)];
  skill.usesLeft += 1;
  log.push(`${fighter.side}の${skill.name}がもう1回使える`);
}

function endRound(player, enemy, log, rng) {
  const random = rng || Math.random;
  [player, enemy].forEach((fighter) => {
    auraList(fighter, "regen").forEach((entry) => {
      const raw = Math.max(1, Math.round(fighter.maxHp * entry.value));
      const amount = receiveHeal(fighter, raw);
      if (amount > 0) {
        fighter.hp = Math.min(fighter.maxHp, fighter.hp + amount);
        log.push(`${fighter.side}は ${amount} 回復した`);
      } else {
        log.push(`${fighter.side}は回復できなかった`);
      }
    });
  });
  [player, enemy].forEach((fighter) => {
    auraList(fighter, "poison").forEach((entry) => {
      fighter.hp -= entry.dot;
      log.push(`${fighter.side}は毒で ${entry.dot} ダメージ`);
    });
    if (fighter.seal) {
      fighter.seal.rounds -= 1;
      if (fighter.seal.rounds <= 0) fighter.seal = null;
    }
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
    rechargeQuestion(fighter, log, random);
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
      player: aiPick(player, enemy),
      enemy: aiPick(enemy, player),
    };
    const order = turnOrder(player, enemy, random);
    for (let i = 0; i < order.length; i += 1) {
      const actor = order[i];
      const target = actor === player ? enemy : player;
      if (!alive(actor) || !alive(target)) break;
      const skill = skillToAct(actor, actor === player ? chosen.player : chosen.enemy, log);
      if (skill) act(actor, target, skill, 1, random, log);
    }
    if (alive(player) && alive(enemy)) endRound(player, enemy, log, random);
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
  return "威力1 / 1ヒット / QTEなし / 回数無制限 / 会心5%。技封じの対象外。";
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
    amp.gain.setValueAtTime(0.001, now);
    amp.gain.exponentialRampToValueAtTime(Math.max(0.002, gain), now + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.001, now + Math.max(dur, 0.03));
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
  miss() {
    this.beep(392, 0.09, "sine", 0.05);
    setTimeout(() => this.beep(311, 0.16, "sine", 0.04), 90);
  },
  heal() {
    this.beep(480, 0.14, "sine", 0.045, 720);
  },
  select() {
    this.beep(340, 0.05, "sine", 0.03);
  },
  battle() {
    this.beep(392, 0.12, "sine", 0.06);
    setTimeout(() => this.beep(494, 0.12, "sine", 0.06), 140);
    setTimeout(() => this.beep(587, 0.28, "sine", 0.055), 280);
  },
  round() {
    this.beep(523, 0.08, "sine", 0.045);
    setTimeout(() => this.beep(659, 0.14, "sine", 0.04), 110);
  },
  turn(yours) {
    this.beep(yours ? 698 : 349, 0.1, "sine", 0.04);
  },
  cast() {
    this.beep(440, 0.07, "sine", 0.035);
    setTimeout(() => this.beep(554, 0.1, "sine", 0.03), 70);
  },
  buff() {
    this.beep(523, 0.08, "sine", 0.04);
    setTimeout(() => this.beep(659, 0.16, "sine", 0.038), 90);
  },
  debuff() {
    this.beep(440, 0.08, "sine", 0.035);
    setTimeout(() => this.beep(370, 0.16, "sine", 0.03), 90);
  },
  poison() {
    this.beep(196, 0.08, "sine", 0.04);
    setTimeout(() => this.beep(165, 0.16, "sine", 0.03), 80);
  },
  stuck() {
    this.beep(294, 0.1, "sine", 0.035);
    setTimeout(() => this.beep(247, 0.14, "sine", 0.03), 100);
  },
  recharge() {
    this.beep(440, 0.07, "sine", 0.035);
    setTimeout(() => this.beep(659, 0.12, "sine", 0.035), 80);
  },
  qteStart() {
    this.beep(880, 0.04, "sine", 0.025);
  },
  draw() {
    this.beep(349, 0.12, "sine", 0.04);
    setTimeout(() => this.beep(349, 0.16, "sine", 0.032), 160);
  },
  qte(label) {
    if (label === "PERFECT") this.beep(880, 0.16, "triangle", 0.05, 1320);
    else if (label === "GOOD") this.beep(700, 0.12, "triangle", 0.045);
    else if (label === "success") this.beep(560, 0.1, "sine", 0.04);
    else this.miss();
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

function withMissColor(text) {
  return escapeHtml(text).replace(/ミス\d+(?:\.\d+)?%/g, (hit) => `<span class="miss-rate">${hit}</span>`);
}

const STATUS_AURAS = [
  { id: "poison", glyph: "☠️", short: "毒", name: "毒", tone: "bad", detail: "ラウンドの終わりにダメージ" },
  { id: "healDown", glyph: "💔", short: "回−", name: "回復量ダウン", tone: "down", detail: "回復量が下がっている" },
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

function pct(value) {
  return Math.round(value * 100);
}

function statusDetail(fighter, spec, list) {
  const sum = list.reduce((total, entry) => total + entry.value, 0);
  if (spec.id === "healDown") return `回復量−${pct(Math.min(CAP.healDown, sum))}%`;
  if (spec.id === "poison") {
    const dot = list.reduce((total, entry) => total + (entry.dot || 0), 0);
    return `ラウンドの終わりに ${dot} ダメージ`;
  }
  if (spec.id === "atkDown") return `攻撃−${pct(Math.min(CAP.down, sum))}%`;
  if (spec.id === "defDown") return `守備−${pct(Math.min(CAP.down, sum))}%`;
  if (spec.id === "atkUp") return `攻撃+${pct(Math.min(CAP.up, sum))}%`;
  if (spec.id === "defUp") return `守備+${pct(Math.min(CAP.defUp, sum))}%`;
  if (spec.id === "power") return `技の威力+${pct(sum)}%`;
  if (spec.id === "critUp") return `会心率+${pct(Math.min(CAP.crit, sum))}%`;
  if (spec.id === "cut") return `受けるダメージを${pct(Math.min(CAP.cut, sum))}%軽減`;
  if (spec.id === "evasion") return `回避${pct(Math.min(CAP.evasion, sum))}%`;
  if (spec.id === "regen") {
    const amount = list.reduce((total, entry) => total + Math.max(1, Math.round(fighter.maxHp * entry.value)), 0);
    return `ラウンドの終わりに ${amount} 回復`;
  }
  if (spec.id === "qteSlow") return "タイミングバーが約3倍ゆっくり";
  return spec.detail;
}

function statusItems(fighter) {
  const items = [];
  STATUS_AURAS.forEach((spec) => {
    const list = auraList(fighter, spec.id);
    if (!list.length) return;
    const fresh = list.some((entry) => entry.fresh);
    const rounds = list.reduce((max, entry) => Math.max(max, entry.rounds), 0);
    items.push({ ...spec, detail: statusDetail(fighter, spec, list), rounds, fresh });
  });
  if (fighter.charges.guard.length) {
    const guard = Math.min(CAP.cut, fighter.charges.guard.reduce((sum, item) => sum + item.value, 0));
    items.push({ id: "guard", glyph: "🛡️", short: "防", name: "ガード", tone: "up", detail: `次の攻撃の初撃を${pct(guard)}%軽減`, rounds: null });
  }
  if (fighter.charges.counter.length) {
    const counter = fighter.charges.counter.reduce((sum, item) => sum + item.value, 0);
    items.push({ id: "counter", glyph: "↩️", short: "反撃", name: "反撃待ち", tone: "up", detail: `次の攻撃の初撃の${pct(counter)}%を返す`, rounds: null });
  }
  if (fighter.charges.sureHit) items.push({ id: "sureHit", glyph: "🎯", short: "必中", name: "必中", tone: "up", detail: "次の攻撃の初撃は必中", rounds: null });
  if (fighter.charges.sureCrit) items.push({ id: "sureCrit", glyph: "💥", short: "必会", name: "会心必中", tone: "up", detail: "次の攻撃の初撃は会心（ダメージ1.5倍）", rounds: null });
  if (fighter.charges.nextPower) items.push({ id: "nextPower", glyph: "⬆️", short: "次威", name: "次の威力アップ", tone: "up", detail: `次の攻撃の初撃の威力+${pct(fighter.charges.nextPower)}%`, rounds: null });
  if (fighter.seal) {
    items.push({
      id: "seal",
      glyph: "🚫",
      short: "封じ",
      name: `${fighter.seal.name}封じ`,
      tone: "bad",
      detail: `${fighter.seal.name}は出せない。通常攻撃は出せる`,
      rounds: fighter.seal.rounds,
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
    <button type="button" class="badge ${item.tone}${item.fresh ? " just" : ""}" data-badge="${key}:${item.id}" aria-label="${escapeHtml(item.name)}">
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

function portraitHtml(type, extraClass, buttonId) {
  const cls = extraClass ? ` ${extraClass}` : "";
  const open = buttonId
    ? `<button type="button" class="portrait${cls}" id="${buttonId}" aria-label="ステータスを見る">`
    : `<div class="portrait${cls}">`;
  const close = buttonId ? "</button>" : "</div>";
  return `${open}<img src="${PORTRAITS[type] || ""}" alt="" onerror="this.hidden=true"><span>イラスト<br>${escapeHtml(type)}</span>${close}`;
}

function showFighterStats(fighter) {
  const atk = Math.round(currentAtk(fighter));
  const def = Math.round(currentDef(fighter));
  const traitCrit = fighter.type === "ネコ科" ? 0.08 : 0;
  const critNow = Math.min(CAP.crit, traitCrit + auraSum(fighter, "critUp"));
  const line = (label, base, now) => (
    now === base
      ? `<p><strong>${label}</strong>　${base}</p>`
      : `<p><strong>${label}</strong>　${base} → ${now}</p>`
  );
  let critLine = "";
  if (fighter.charges.sureCrit) critLine = `<p><strong>会心</strong>　次の攻撃は100%</p>`;
  else if (critNow > traitCrit) {
    critLine = traitCrit > 0
      ? `<p><strong>会心</strong>　+${pct(traitCrit)}% → +${pct(critNow)}%</p>`
      : `<p><strong>会心</strong>　+${pct(critNow)}%</p>`;
  } else if (critNow > 0) critLine = `<p><strong>会心</strong>　+${pct(critNow)}%</p>`;
  showSheet(`
    <h2>${escapeHtml(fighter.side)}・${escapeHtml(fighter.type)}</h2>
    <p><strong>HP</strong>　${Math.max(0, fighter.hp)} / ${fighter.maxHp}</p>
    ${line("攻撃", fighter.atk, atk)}
    ${line("守備", fighter.def, def)}
    <p><strong>素早さ</strong>　${fighter.spd}</p>
    ${critLine}
    ${fighter.trait ? `<p><strong>特性</strong>　${escapeHtml(fighter.trait)}</p>` : ""}
    <button class="primary" data-close type="button">閉じる</button>
  `);
}

function renderBattle(view) {
  const app = document.getElementById("app");
  const prev = shownHp || { player: view.player.hp, enemy: view.enemy.hp };
  const recent = view.log.slice(-3);
  const hud = (fighter, key) => {
    const from = Math.max(0, prev[key]) / fighter.maxHp;
    return `
      <section class="hud">
        <div class="hud-top">
          <h2>${escapeHtml(fighter.side)}・${escapeHtml(fighter.type)}</h2>
          <p>HP ${Math.max(0, fighter.hp)} / ${fighter.maxHp}</p>
        </div>
        <div class="hp ${fighter.hp / fighter.maxHp <= 0.3 ? "low" : ""}" id="hp-${key}"><span id="fill-${key}" style="width:${Math.max(0, Math.min(1, from)) * 100}%"></span></div>
        <div class="hud-top foot">
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
    ? `<div class="qte ${view.player.type === "鳥類" ? "wide" : ""}" id="qte"><div class="good" style="${qteBandStyle(view.qteLayout, "good")}"></div><div class="perfect" style="${qteBandStyle(view.qteLayout, "perfect")}"></div><div class="core" style="${qteBandStyle(view.qteLayout, "core")}"></div><div class="marker" id="marker"></div></div><button class="primary" id="qte-stop" type="button">今だ！</button>`
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
      <div class="logline">
        <div class="feed">${recent.length ? recent.map((line, index) => `<p class="${index === recent.length - 1 ? "now" : ""}">${escapeHtml(line)}</p>`).join("") : `<p class="now">戦いがはじまる</p>`}</div>
        <button type="button" id="open-log">ログ</button>
      </div>
      <div class="field">
        <div class="ground"></div>
        <div class="actor enemy" id="card-enemy">${portraitHtml(view.enemy.type, "field-art")}</div>
        <div class="actor player" id="card-player">${portraitHtml(view.player.type, "field-art", "open-stats")}</div>
        ${view.banner ? `<p class="banner ${view.bannerSide || ""}">${escapeHtml(view.banner)}</p>` : ""}
        ${view.finale ? finaleHtml(view.finale) : ""}
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
  const openStats = document.getElementById("open-stats");
  if (openStats) openStats.onclick = () => showFighterStats(view.player);
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
    const grants = (view.fxGrant || {})[key] || [];
    if (grants.length) stampGrants(document.getElementById(`card-${key}`), grants);
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
    if (crit) stampImpact(cardEl, cut ? "pop high" : "pop", { glyph: "🎯", short: "会心", tone: "up" });
    if (cut) stampImpact(cardEl, crit ? "pop low" : "pop", { glyph: "🛡️", short: "防", tone: "up" });
    if (view.actor) {
      Sfx[delta < 0 ? "hit" : "heal"](crit);
      if (cut) Sfx.guard();
    }
    if (delta < 0) {
      app.classList.remove("shake");
      app.getBoundingClientRect();
      app.classList.add("shake");
    }
  });
  if (view.whiff) {
    const cardEl = document.getElementById(view.whiff === "あなた" ? "card-player" : "card-enemy");
    if (cardEl) {
      const evaded = view.whiffKind === "evade";
      stampImpact(cardEl, "pop", evaded
        ? { glyph: "💨", short: "回避", tone: "up" }
        : { glyph: "💨", short: "ミス", tone: "down" });
      Sfx.miss();
    }
  }
  if (view.actor) {
    const actorCard = document.getElementById(view.actor === "あなた" ? "card-player" : "card-enemy");
    if (actorCard) actorCard.classList.add("swing");
  }
  if (view.finished) {
    if (view.phaseText.includes("勝ち")) Sfx.win();
    else if (view.phaseText.includes("負け")) Sfx.lose();
    else Sfx.draw();
  }
  shownHp = { player: view.player.hp, enemy: view.enemy.hp };
  const log = document.getElementById("log");
  if (log) log.scrollTop = log.scrollHeight;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function sideOf(actor) {
  return actor.side === "あなた" ? "you" : "foe";
}

function finaleHtml(word) {
  const tone = word === "勝ち" ? "win" : word === "負け" ? "lose" : "draw";
  const kicker = word === "勝ち" ? "WIN" : word === "負け" ? "LOSE" : "DRAW";
  const sub = word === "勝ち" ? "相手を倒した" : word === "負け" ? "倒されてしまった" : "決着がつかなかった";
  return `<div class="finale ${tone}"><p class="finale-kicker">${kicker}</p><p class="finale-word">${escapeHtml(word)}</p><p class="finale-sub">${sub}</p></div>`;
}

function qteWindow(wide) {
  const scale = wide ? 1.5 : 1;
  const perfectHalf = 0.03 * scale;
  const goodHalf = 0.08 * scale;
  const coreHalf = 0.008 * scale;
  const min = Math.max(0.3, goodHalf);
  const max = Math.min(0.7, 1 - goodHalf);
  return {
    center: min + Math.random() * (max - min),
    coreHalf,
    perfectHalf,
    goodHalf,
  };
}

function qteBandStyle(layout, band) {
  if (!layout) return "";
  const half = band === "core" ? layout.coreHalf : band === "perfect" ? layout.perfectHalf : layout.goodHalf;
  return `left:${(layout.center - half) * 100}%;width:${half * 200}%`;
}

function qteResult(dist, layout) {
  if (dist <= layout.coreHalf) return { mult: 1.5, label: "PERFECT" };
  if (dist <= layout.perfectHalf) return { mult: 1.2, label: "GOOD" };
  if (dist <= layout.goodHalf) return { mult: 1, label: "success" };
  return { mult: 0.5, label: "miss" };
}

function askQte(slow, layout) {
  return new Promise((resolve) => {
    const marker = document.getElementById("marker");
    const button = document.getElementById("qte-stop");
    const period = slow ? 3300 : 1100;
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
      resolve(qteResult(dist, layout));
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

function whiffOf(lines, actorSide) {
  if (lines.some((line) => line.includes("あなたは") && line.includes("回避"))) return "あなた";
  if (lines.some((line) => line.includes("相手は") && line.includes("回避"))) return "相手";
  if (lines.some((line) => line.includes("外れた"))) return actorSide === "あなた" ? "相手" : "あなた";
  return "";
}

function stampGrants(cardEl, items) {
  const portrait = cardEl && cardEl.querySelector(".portrait");
  if (!portrait) return;
  const row = document.createElement("div");
  row.className = "impact grant";
  row.innerHTML = items.map((item) => `<span class="badge ${item.tone}"><span class="glyph">${item.glyph}</span><span class="bname">${escapeHtml(item.name)}</span></span>`).join("");
  portrait.appendChild(row);
}

function stampImpact(cardEl, kind, item) {
  const portrait = cardEl.querySelector(".portrait");
  if (!portrait) return;
  const stamp = document.createElement("div");
  stamp.className = `impact ${kind}`;
  stamp.innerHTML = `<span class="badge ${item.tone}"><span class="glyph">${item.glyph}</span><span class="bname">${escapeHtml(item.short)}</span></span>`;
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

  renderBattle(view({ banner: "バトル開始！", bannerSide: "start", phaseText: "バトル開始！" }));
  Sfx.battle();
  await wait(1400);

  while (alive(player) && alive(enemy)) {
    renderBattle(view({ command: true, waiting: true, phaseText: "行動を選ぶ" }));
    const playerSkill = await new Promise((resolve) => {
      document.querySelectorAll("[data-skill]").forEach((button) => {
        button.onclick = () => {
          Sfx.select();
          const picked = player.skills[Number(button.dataset.skill)];
          const usable = canUse(player, picked);
          const close = showSheet(`
            <h2>${escapeHtml(picked.name)}</h2>
            <p>${withMissColor(skillBlurb(picked.name))}</p>
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
    const enemySkill = aiPick(enemy, player);
    async function callout(text, ms, side) {
      renderBattle(view({ banner: text, bannerSide: side || "", phaseText: text }));
      if (text.endsWith("ラウンド")) Sfx.round();
      else if (text === "あなたの番") Sfx.turn(true);
      else if (text === "相手の番") Sfx.turn(false);
      await wait(ms);
    }
    function cueSupport(skill) {
      if (skill.foeAuras.length || skill.seal) Sfx.debuff();
      else if (!skill.power && !skill.heal) Sfx.cast();
    }
    await callout(`${round}ラウンド`, 1300);
    const order = turnOrder(player, enemy, Math.random);
    for (let i = 0; i < order.length; i += 1) {
      const actor = order[i];
      const target = actor === player ? enemy : player;
      if (!alive(actor) || !alive(target)) break;
      const planned = actor === player ? playerSkill : enemySkill;
      const skill = skillToAct(actor, planned, log);
      const side = sideOf(actor);
      await callout(actor.side === "あなた" ? "あなたの番" : "相手の番", 1100, side);
      if (!skill) {
        renderBattle(view({ banner: "動けない", bannerSide: side, phaseText: `${actor.side}は動けなかった` }));
        Sfx.stuck();
        await wait(1100);
        continue;
      }
      let qte = 1;
      if (actor === player && skill.qte) {
        const qteLayout = qteWindow(player.type === "鳥類");
        renderBattle(view({ banner: skill.name, bannerSide: side, qte: true, qteLayout, phaseText: `${skill.name}：赤い線で止める` }));
        Sfx.qteStart();
        const result = await askQte(auraSum(player, "qteSlow") > 0, qteLayout);
        qte = result.mult;
        Sfx.qte(result.label);
        log.push(`QTE ${result.label}`);
        const bar = document.getElementById("qte");
        if (bar) {
          bar.className = "qte result";
          bar.innerHTML = `<p class="qte-result" data-qte="${escapeHtml(result.label)}">${escapeHtml(result.label)}</p>`;
        }
        await wait(800);
      }
      if (skill.power && skill.hits > 1) {
        await playCombo(actor, target, skill, qte, log, view);
        finishAct(actor, target, skill, log);
      } else {
        const mark = log.length;
        act(actor, target, skill, qte, Math.random, log);
        const slice = log.slice(mark);
        cueSupport(skill);
        renderBattle(view({
          banner: skill.name,
          bannerSide: side,
          phaseText: skill.name,
          actor: actor.side,
          fxCrit: fxCrit(slice),
          fxCut: fxCut(slice),
          whiff: whiffOf(slice, actor.side),
          whiffKind: slice.some((line) => line.includes("回避")) ? "evade" : "",
        }));
        await wait(1500);
      }
      const buffs = buffGrants(skill);
      if (buffs.length) {
        const key = actor.side === "あなた" ? "player" : "enemy";
        renderBattle(view({
          banner: buffs.map((item) => item.name).join("・"),
          bannerSide: side,
          phaseText: "バフ",
          fxGrant: { [key]: buffs },
        }));
        Sfx.buff();
        await wait(1700);
      }
    }
    if (alive(player) && alive(enemy)) {
      const before = log.length;
      endRound(player, enemy, log, Math.random);
      const tail = log.slice(before);
      if (tail.some((line) => line.includes("毒で"))) Sfx.poison();
      if (tail.some((line) => line.includes("回復した"))) Sfx.heal();
      if (tail.some((line) => line.includes("もう1回使える"))) Sfx.recharge();
      round += 1;
    } else break;
  }

  finished = true;
  let phaseText = "引き分け";
  if (player.hp > 0 && enemy.hp <= 0) phaseText = "勝ち";
  else if (enemy.hp > 0 && player.hp <= 0) phaseText = "負け";
  player.hp = Math.max(0, player.hp);
  enemy.hp = Math.max(0, enemy.hp);
  shownHp = { player: player.hp, enemy: enemy.hp };
  renderBattle(view({ phaseText, finished: true, finale: phaseText }));
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
if (typeof window !== "undefined") {
  window.AnimalBattle = AnimalBattle;
  window.Sfx = Sfx;
  const unlock = () => {
    const ctx = Sfx.ensure();
    if (ctx && ctx.state === "suspended") ctx.resume();
  };
  document.addEventListener("pointerdown", unlock);
}
if (typeof module !== "undefined" && module.exports) module.exports = AnimalBattle;
