// 友人戦（2026-10-02 ゆーしん「ポケモンバトルみたいに、相手と自分のやってることが合うように」）
// メンバーの battle.js の仕組み（makeFighter・turnOrder・act・endRound・renderBattle・askQte など）をそのまま使い、
// 「相手をコンピューターが動かす」ところだけを「相手のスマホで選んだ技を待つ」にかえたもの。battle.js には手を入れていない。
//
// 2人の画面で結果が同じになるように：
// - 乱数は、サーバーが決めた同じ「たね」から作る（Math.random は使わない）
// - 行動の順番・ダメージの計算は、番号の小さい方（lo）→大きい方（hi）の決まった並びで呼ぶ
// - タイミングバー（QTE）は、その技を出す人のスマホだけで押し、結果の倍率を相手にも送る
// - 連続攻撃のアニメ（battle.js の playCombo）は中で Math.random を使うので、その間だけ同じたねの乱数に差しかえる
// 2026-10-02 battle.js ef25461 に合わせた（ラウンドの上限なし・連続攻撃のアニメ・タイミングの帯の位置）
(function () {
  function seeded(seed) {   // mulberry32：同じたねなら、どの端末でも同じ数が同じ順で出る
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  async function send(m, body) {
    for (let i = 0; i < 5; i += 1) {   // 電波が悪くても何回か送り直す
      try {
        const r = await fetch('/api/pvp/act', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ match: m.id, token: m.token, ...body }) });
        if (r.ok) return true;
      } catch (e) {}
      await wait(800);
    }
    return false;
  }

  // 条件がそろうまで、0.7秒ごとに試合の状態を見に行く。90秒来なければ null
  async function until(m, check) {
    const start = Date.now();
    while (Date.now() - start < 90000) {
      try {
        const s = await (await fetch(`/api/pvp/state?match=${m.id}&token=${encodeURIComponent(m.token)}`)).json();
        const v = s.ok ? check(s) : undefined;
        if (v !== undefined && v !== null) return v;
      } catch (e) {}
      await wait(700);
    }
    return null;
  }

  async function playPvp(m) {
    // m = { id, token, seed, side: "lo"|"hi", me, meMonth, foe, foeMonth }
    const rng = seeded(m.seed);
    const player = makeFighter("あなた", m.me, m.meMonth);
    const enemy = makeFighter("相手", m.foe, m.foeMonth);
    const lo = m.side === "lo" ? player : enemy, hi = m.side === "lo" ? enemy : player;
    const mine = m.side, theirs = m.side === "lo" ? "hi" : "lo";
    shownHp = null;
    Sfx.ensure();
    const log = [`相手は${enemy.type}（${enemy.month}月）`];
    let round = 1, finished = false;
    const view = (extra) => ({ player, enemy, log: log.slice(), round, waiting: false, qte: false, finished, phaseText: "", ...extra });

    function lost(text) {   // 相手の通信が切れたとき
      finished = true;
      renderBattle(view({ phaseText: text, finished: true }));
    }

    while (alive(player) && alive(enemy)) {
      // 1. 自分の技を選ぶ（選び方は battle.js と同じ）
      renderBattle(view({ command: true, waiting: true, phaseText: "行動を選ぶ" }));
      const picked = await new Promise((resolve) => {
        document.querySelectorAll("[data-skill]").forEach((button) => {
          button.onclick = () => {
            const skill = player.skills[Number(button.dataset.skill)];
            const usable = canUse(player, skill);
            const close = showSheet(`
              <h2>${escapeHtml(skill.name)}</h2>
              <p>${escapeHtml(skillBlurb(skill.name))}</p>
              ${usable ? `<button class="primary" id="use-skill" type="button">これに決める</button>` : `<p class="detail">今は使えない</p>`}
              <button class="ghost" data-close type="button">戻る</button>`);
            const use = document.getElementById("use-skill");
            if (use) use.onclick = () => { close(); resolve(Number(button.dataset.skill)); };
          };
        });
      });
      Sfx.select();
      await send(m, { kind: "pick", round, value: picked });

      // 2. 相手が選ぶのを待つ
      renderBattle(view({ phaseText: "相手が技を選んでいます…", picks: { player: player.skills[picked].name, enemy: "考え中…" } }));
      const foePick = await until(m, (s) => (s.picks[String(round)] || {})[theirs]);
      if (foePick == null) { lost("相手の通信が切れました"); break; }
      const plan = { [mine]: player.skills[picked], [theirs]: enemy.skills[foePick] };

      // 3. 2人の技を同時に見せる
      renderBattle(view({ phaseText: "おたがいの技が決まった！", picks: { player: plan[mine].name, enemy: plan[theirs].name } }));
      await wait(1100);

      // 4. 順番に行動する（2人の画面で同じ順・同じ乱数）
      const order = turnOrder(lo, hi, rng);
      let broken = false;
      for (let i = 0; i < order.length; i += 1) {
        const actor = order[i];
        const target = actor === lo ? hi : lo;
        if (!alive(actor) || !alive(target)) break;
        const skill = skillToAct(actor, plan[actor === lo ? "lo" : "hi"], log);
        if (!skill) {
          renderBattle(view({ phaseText: `${actor.side}は動けなかった` }));
          await wait(700);
          continue;
        }
        let qte = 1;
        if (skill.qte && actor === player) {
          const qteLayout = qteWindow(player.type === "鳥類");   // 帯の位置は自分の画面だけのこと（結果の倍率だけ相手に送る）
          renderBattle(view({ qte: true, qteLayout, phaseText: `${skill.name}：緑の帯で止める` }));
          const result = await askQte(auraSum(player, "qteSlow") > 0, qteLayout);
          qte = result.mult;
          Sfx.qte(result.label);
          const stop = document.getElementById("qte-stop");
          if (stop) stop.textContent = result.label;
          log.push(`QTE ${result.label}`);
          await send(m, { kind: "qte", round, step: i, value: qte });
          await wait(380);
        } else if (skill.qte) {
          renderBattle(view({ phaseText: `相手が${skill.name}のタイミングを合わせています…` }));
          const v = await until(m, (s) => s.qte[`${round}-${i}`]);
          if (v == null) { broken = true; break; }
          qte = v;
        } else if (actor !== player) {
          renderBattle(view({ phaseText: "相手の行動" }));
          await wait(450);
        }
        if (skill.power && skill.hits > 1) {
          // 連続攻撃：1発ずつアニメで見せる。中の乱数を同じたねのものにする
          const original = Math.random;
          Math.random = rng;
          try { await playCombo(actor, target, skill, qte, log, view); } finally { Math.random = original; }
          finishAct(actor, target, skill, log);
        } else {
          const mark = log.length;
          act(actor, target, skill, qte, rng, log);
          renderBattle(view({ phaseText: `${actor.side}の${skill.name}`, actor: actor.side,
            fxCrit: fxCrit(log.slice(mark)), fxCut: fxCut(log.slice(mark)) }));
          await wait(900);
        }
      }
      if (broken) { lost("相手の通信が切れました"); break; }
      if (alive(player) && alive(enemy)) {
        const mark = log.length;
        endRound(lo, hi, log);
        round += 1;
        if (log.length > mark) {
          renderBattle(view({ phaseText: "ラウンドの終わり", fxCrit: fxCrit(log.slice(mark)) }));
          await wait(700);
        }
      } else break;
    }

    if (!finished) {
      finished = true;
      let phaseText = "引き分け";
      if (player.hp > 0 && enemy.hp <= 0) phaseText = "勝ち！";
      else if (enemy.hp > 0 && player.hp <= 0) phaseText = "負け…";
      player.hp = Math.max(0, player.hp);
      enemy.hp = Math.max(0, enemy.hp);
      shownHp = { player: player.hp, enemy: enemy.hp };
      renderBattle(view({ phaseText, finished: true }));
      send(m, { kind: "done" });
    }
  }

  window.playPvp = playPvp;
})();
